from flask import Flask, jsonify
import requests
from web3 import Web3
import os

app = Flask(__name__)

# --- CONFIGURACIÓN ROBUSTA ---
# Si no encuentra la variable RPC_URL, usará el nodo público de Binance por defecto
RPC_URL = os.getenv('RPC_URL', 'https://bsc-dataseed.binance.org/')
w3 = Web3(Web3.HTTPProvider(RPC_URL))

PRIVATE_KEY = os.getenv('PRIVATE_KEY')
CONTRATO_POOL = os.getenv('CONTRACT_ADDRESS')
NODO_URL = os.getenv('NODO_MAESTRO_URL', 'https://binance-bot-hna7.onrender.com')

# ABI resumido del contrato (asegúrate de que coincida con el nombre de la función en Solidity)
ABI_MINIMO = [{"inputs":[{"internalType":"uint256","name":"_total","type":"uint256"}],"name":"sincronizarMineria","outputs":[],"stateMutability":"nonpayable","type":"function"}]

@app.route('/')
def home():
    return jsonify({"mensaje": "Servidor CharlyCoin Economy Bridge Activo"}), 200

@app.route('/sincronizar-ahora', methods=['GET'])
def sincronizar():
    try:
        # 1. Verificación de seguridad inicial
        if not PRIVATE_KEY or not CONTRATO_POOL:
            return jsonify({"error": "Faltan variables de entorno (KEY o ADDRESS)"}), 500

        # Obtener la dirección de la billetera desde la Private Key
        cuenta = w3.eth.account.from_key(PRIVATE_KEY)
        mi_direccion = cuenta.address

        # 2. Leer el CharlyScan (tu otro servicio)
        response = requests.get(f"{NODO_URL}/cadena")
        cadena = response.json()
        
        # 3. Calcular el total supply sumando los montos de los bloques
        total_chc = sum(float(bloque['transacciones'][0]['monto']) for bloque in cadena if bloque['transacciones'])

        # 4. Preparar la transacción para la Blockchain
        contract = w3.eth.contract(address=w3.to_checksum_address(CONTRATO_POOL), abi=ABI_MINIMO)
        nonce = w3.eth.get_transaction_count(mi_direccion)
        
        # Construir transacción
        tx = contract.functions.sincronizarMineria(int(total_chc)).build_transaction({
            'chainId': 56, # 56 es Mainnet de Binance
            'gas': 100000, # Subimos un poco el límite por seguridad
            'gasPrice': w3.to_wei('3', 'gwei'),
            'nonce': nonce,
        })

        # 5. Firmar y enviar
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return jsonify({
            "status": "Sincronizado",
            "total_chc": total_chc,
            "billetera_operadora": mi_direccion,
            "tx_hash": w3.to_hex(tx_hash)
        }), 200

    except Exception as e:
        # Si el error es por falta de saldo o conexión, aquí lo dirá claramente
        return jsonify({"error": f"Error en la operacion: {str(e)}"}), 500

if __name__ == "__main__":
    # Render usa el puerto 10000 por defecto para Python
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
