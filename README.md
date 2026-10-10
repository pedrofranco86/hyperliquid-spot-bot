# Bot de Micro-Grid / Scalping Spot (HYPE/USDC) en Hyperliquid

Este bot ejecuta una estrategia de **Scalping Reactivo y Micro-Grid en el mercado Spot HYPE/USDC** en la plataforma **Hyperliquid**, optimizado para operar con saldo dinámico a partir de **~$10 USD**.

---

## 🚀 Características Principales

1. **Gestión Dinámica de Capital:** Detecta automáticamente el saldo en USDC y HYPE en tu cuenta Spot. Modula el tamaño de las órdenes a partir de $10 USD (mínimo recomendado por Hyperliquid Spot).
2. **Garantía Maker (Post-Only / ALO):** Utiliza órdenes `limit` con `tif: Alo`. Si la orden cruza el spread, el exchange la rechaza en lugar de cobrar la tarifa Taker. Paga únicamente la tarifa Maker base de **0.040%** por orden (**0.080% roundtrip**).
3. **Escalón de Beneficio Neto:** Configurado por defecto al **1.00%**, lo que deja un beneficio neto estimado de **~0.92% por ciclo completado** tras comisiones.
4. **Dead Man's Switch de Seguridad:** Activa `schedule_cancel` a 30 segundos en cada ciclo. Si el bot pierde conexión o se apaga el VPS/PC, todas las órdenes pendientes se cancelan automáticamente en el servidor para evitar órdenes huérfanas.
5. **Control de Inventario:** Detiene compras automáticamente si el activo HYPE supera el **85% del capital total** de la cuenta, evitando acumulación masiva si el mercado entra en tendencia bajista fuerte.
6. **Sin Apalancamiento ni Liquidación:** Al operar exclusivamente en el DEX **Spot**, no existen riesgos de liquidación ni cargos por *Funding Rate*.

---

## 🛠️ Guía de Instalación y Configuración

### 1. Requisitos Previos
* Python 3.9 o superior.
* Una cuenta en Hyperliquid con saldo Spot (USDC y/o HYPE).

### 2. Configurar Entorno e Claves
Crea el archivo `.env` copiando la plantilla:

```bash
cp .env.example .env
```

Edita `.env` con tus claves:
```env
HL_WALLET_ADDRESS=0xTuDireccion0x...
HL_PRIVATE_KEY=0xTuClavePrivada...
HL_ENV=MAINNET
```

### 3. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecución del Bot
Para probar o ejecutar el bot:
```bash
python bot.py
```

Para mantenerlo ejecutando 24/7 en un servidor Linux (VPS):
```bash
nohup python bot.py > bot.log 2>&1 &
```

---

## 📊 Estructura de Archivos

```
hyperliquid_spot_bot/
├── config.py         # Configuración de límites, paso de red, umbrales y tiempos
├── bot.py            # Script principal con la lógica de trading y ejecuciones ALO
├── requirements.txt  # Librerías necesarias (hyperliquid-python-sdk, eth-account, etc.)
├── .env.example      # Plantilla de variables de entorno
└── README.md         # Documentación del proyecto
```
