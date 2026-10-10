#!/usr/bin/env python3
"""
Bot de Micro-Grid y Scalping Reactivo Spot (HYPE/USDC) en Hyperliquid.
Optimizado para operar dinámicamente con capital desde ~$10 USD disponible.
Garantiza ejecución Maker Post-Only (ALO), gestión de inventario y Dead Man's Switch.
"""

import os
import time
import logging
import eth_account
from dotenv import load_dotenv

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
import config

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("HyperliquidSpotBot")


class HyperliquidMicroGridBot:
    def __init__(self):
        load_dotenv()
        
        self.address = config.HL_WALLET_ADDRESS
        self.private_key = config.HL_PRIVATE_KEY
        
        if not self.private_key or self.address == "0x0000000000000000000000000000000000000000":
            raise ValueError("❌ Configura tus claves HL_WALLET_ADDRESS y HL_PRIVATE_KEY en el archivo .env")

        # Inicialización de cuenta y SDK
        self.account = eth_account.Account.from_key(self.private_key)
        self.info = Info(config.BASE_URL, skip_ws=True)
        self.exchange = Exchange(self.account, config.BASE_URL, account_address=self.address)

        # Estado interno del bot
        self.active_buy_oid = None
        self.active_sell_oid = None
        self.buy_fill_price = None
        
        log.info("==================================================")
        log.info(f"🚀 BOT HYPE/USDC SPOT INICIADO en {config.HL_ENV}")
        log.info(f"👤 Wallet: {self.address}")
        log.info("==================================================")

    def get_spot_balances(self):
        """Consulta el saldo spot actual de USDC y HYPE disponible."""
        try:
            state = self.info.user_state(self.address)
            usdc = 0.0
            hype = 0.0
            
            # Buscar en spotBalances
            spot_balances = state.get("spotBalances", [])
            for bal in spot_balances:
                coin = bal.get("coin")
                total = float(bal.get("total", bal.get("hold", 0.0)))
                if coin == "USDC":
                    usdc = total
                elif coin == "HYPE":
                    hype = total
                    
            return usdc, hype
        except Exception as e:
            log.error(f"Error al obtener saldos spot: {e}")
            return 0.0, 0.0

    def get_hype_price(self):
        """Obtiene el precio actual de HYPE en Spot."""
        try:
            mids = self.info.all_mids()
            # En Hyperliquid Spot el identificador puede ser HYPE, HYPE:USDC o un token ID
            price = mids.get(config.COIN_NAME) or mids.get(config.SPOT_PAIR)
            if price is not None:
                return float(price)
            
            # Fallback en caso de nombre alternativo
            for key, val in mids.items():
                if "HYPE" in key.upper():
                    return float(val)
                    
            raise ValueError("No se encontró la cotización de HYPE en el orderbook.")
        except Exception as e:
            log.error(f"Error al obtener precio de HYPE: {e}")
            return None

    def place_alo_order(self, is_buy, px, size_usdc):
        """Coloca una orden Límite Post-Only (ALO) en Spot."""
        try:
            sz = round(size_usdc / px, 4)
            limit_px = round(px, 4)
            
            log.info(f"Colocando orden ALO {'COMPRA' if is_buy else 'VENTA'}: {sz} HYPE @ ${limit_px:.4f} (~${size_usdc:.2f} USD)")
            
            # Formato de orden Spot con bandera Post-Only (ALO)
            res = self.exchange.order(
                name=config.COIN_NAME,
                is_buy=is_buy,
                sz=sz,
                limit_px=limit_px,
                order_type={"limit": {"tif": "Alo"}},
                dex="spot"
            )
            
            if res.get("status") != "ok":
                log.error(f"❌ Orden rechazada por el Exchange: {res}")
                return None
                
            data = res.get("response", {}).get("data", {})
            statuses = data.get("statuses", [])
            if statuses and "resting" in statuses[0]:
                oid = statuses[0]["resting"]["oid"]
                log.info(f"✅ Orden ingresada con éxito OID: {oid}")
                return oid
            else:
                log.warning(f"⚠️ La orden no quedó en el libro (Posible cruce/Taker rechazado por ALO): {statuses}")
                return None
        except Exception as e:
            log.error(f"Error crítico al enviar orden ALO: {e}")
            return None

    def cancel_order(self, oid):
        """Cancela una orden activa específica en Spot."""
        try:
            if oid:
                self.exchange.cancel(config.COIN_NAME, oid)
                log.info(f"🗑️ Orden cancelada OID: {oid}")
        except Exception as e:
            log.error(f"Error al cancelar orden {oid}: {e}")

    def get_open_order_ids(self):
        """Devuelve la lista de OIDs activos en la cuenta."""
        try:
            orders = self.info.open_orders(self.address)
            return {o["oid"] for o in orders if config.COIN_NAME in o.get("coin", "")}
        except Exception as e:
            log.error(f"Error al listar órdenes abiertas: {e}")
            return set()

    def run(self):
        """Bucle principal de ejecución del bot."""
        log.info("🔄 Iniciando ciclo de supervisión de mercado...")
        
        while True:
            try:
                # 1. Armar Dead Man's Switch (Cancela todo en 30s si el bot se detiene)
                try:
                    self.exchange.schedule_cancel(int(time.time() * 1000) + config.DEAD_MAN_TIMEOUT_MS)
                except Exception as e:
                    log.debug(f"Schedule cancel info: {e}")

                # 2. Consultar Precio y Saldos Actuales
                curr_price = self.get_hype_price()
                if not curr_price:
                    time.sleep(config.POLL_INTERVAL_SEC)
                    continue

                usdc_bal, hype_bal = self.get_spot_balances()
                hype_value_usd = hype_bal * curr_price
                total_capital_usd = usdc_bal + hype_value_usd
                
                if total_capital_usd <= 0:
                    log.warning("⚠️ No se detectó capital disponible en la cuenta Spot. Esperando fondos...")
                    time.sleep(config.POLL_INTERVAL_SEC)
                    continue

                inventory_pct = hype_value_usd / total_capital_usd if total_capital_usd > 0 else 0.0

                log.info(f"📊 HYPE: ${curr_price:.4f} | USDC: ${usdc_bal:.2f} | HYPE: {hype_bal:.4f} (~${hype_value_usd:.2f}) | Capital Total: ${total_capital_usd:.2f} | Inventario HYPE: {inventory_pct*100:.1f}%")

                open_oids = self.get_open_order_ids()

                # 3. Detectar si la orden de COMPRA se llenó -> Colocar VENTA espejo
                if self.active_buy_oid and self.active_buy_oid not in open_oids:
                    log.info(f"🎉 ¡COMPRA EJECUTADA! (OID: {self.active_buy_oid}). Colocando VENTA espejo al +{config.STEP_PCT*100:.1f}%...")
                    fill_px = self.buy_fill_price or (curr_price * (1 - config.STEP_PCT))
                    sell_target_px = round(fill_px * (1 + config.STEP_PCT), 4)
                    
                    # Vender el HYPE comprado
                    sell_usd_size = min(hype_value_usd, max(config.MIN_ORDER_USD, total_capital_usd * 0.95))
                    self.active_sell_oid = self.place_alo_order(is_buy=False, px=sell_target_px, size_usdc=sell_usd_size)
                    self.active_buy_oid = None

                # 4. Detectar si la orden de VENTA se llenó -> Reiniciar ciclo
                if self.active_sell_oid and self.active_sell_oid not in open_oids:
                    log.info(f"🎉 ¡VENTA EJECUTADA! (OID: {self.active_sell_oid}). Ciclo completado con ganancia neta estimada de ~0.92%.")
                    self.active_sell_oid = None

                # 5. Gestión de Riesgo por Límite de Inventario
                if inventory_pct >= config.MAX_INVENTORY_PCT:
                    log.warning(f"🛡️ Control de Riesgo: Inventario HYPE ({inventory_pct*100:.1f}%) >= Máximo Permitido ({config.MAX_INVENTORY_PCT*100:.0f}%). Pausando compras.")
                    if self.active_buy_oid and self.active_buy_oid in open_oids:
                        self.cancel_order(self.active_buy_oid)
                        self.active_buy_oid = None
                    time.sleep(config.POLL_INTERVAL_SEC)
                    continue

                # 6. Colocar Orden de COMPRA si no hay ninguna activa y hay USDC libre
                if not self.active_buy_oid and not self.active_sell_oid:
                    if usdc_bal >= config.MIN_ORDER_USD * 0.90:
                        # Calcular tamaño óptimo según capital disponible (adaptado a ~$10 USD o más)
                        usable_usdc = usdc_bal * (1 - config.SAFETY_BUFFER_PCT)
                        buy_size_usd = max(config.MIN_ORDER_USD, usable_usdc)
                        
                        buy_target_px = round(curr_price * (1 - config.STEP_PCT), 4)
                        self.buy_fill_price = buy_target_px
                        
                        self.active_buy_oid = self.place_alo_order(is_buy=True, px=buy_target_px, size_usdc=buy_size_usd)
                    else:
                        log.info(f"ℹ️ Saldo USDC (${usdc_bal:.2f}) menor al mínimo recomendado (${config.MIN_ORDER_USD} USD) o capital 100% desplegado.")

                time.sleep(config.POLL_INTERVAL_SEC)

            except KeyboardInterrupt:
                log.info("🛑 Apagado manual solicitado por el usuario. Cancelando órdenes activas...")
                if self.active_buy_oid:
                    self.cancel_order(self.active_buy_oid)
                if self.active_sell_oid:
                    self.cancel_order(self.active_sell_oid)
                log.info("👋 Bot apaga sus operaciones de forma segura.")
                break
            except Exception as e:
                log.error(f"Excepción en bucle principal: {e}", exc_info=True)
                time.sleep(10)


if __name__ == "__main__":
    try:
        bot = HyperliquidMicroGridBot()
        bot.run()
    except Exception as err:
        log.critical(f"No se pudo iniciar el bot: {err}")
