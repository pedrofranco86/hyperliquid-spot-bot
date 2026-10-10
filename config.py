import os
from dotenv import load_dotenv
from hyperliquid.utils import constants

load_dotenv()

# Credenciales de Hyperliquid
HL_WALLET_ADDRESS = os.getenv("HL_WALLET_ADDRESS", "0x0000000000000000000000000000000000000000")
HL_PRIVATE_KEY = os.getenv("HL_PRIVATE_KEY", "")

# Entorno de red
HL_ENV = os.getenv("HL_ENV", "MAINNET").upper()
BASE_URL = constants.MAINNET_API_URL if HL_ENV == "MAINNET" else constants.TESTNET_API_URL

# Símbolo Spot en Hyperliquid
COIN_NAME = "HYPE"
SPOT_PAIR = "HYPE:USDC"

# Parámetros de Operación Adaptados a Capital Pequeño (~$10 USD+)
MIN_ORDER_USD = 10.0         # Mínimo recomendado por orden en Hyperliquid Spot
STEP_PCT = 0.010             # Escalón de ganancia: 1.0% (Ganancia neta 0.92% descontando fees Maker de 0.080% roundtrip)
SAFETY_BUFFER_PCT = 0.05     # 5% de reserva libre de USDC/HYPE para evitar rechazos por saldo ajustado
MAX_INVENTORY_PCT = 0.85     # Si más del 85% del capital total pasa a HYPE, frena compras y solo ejecuta ventas

# Intervalos y Seguridad
POLL_INTERVAL_SEC = 10       # Frecuencia de chequeo del bucle (10 segundos)
DEAD_MAN_TIMEOUT_MS = 30000  # Dead man's switch: cancela órdenes en 30s si la conexión cae
