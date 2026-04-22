from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from web3 import Web3
import os

app = Flask(__name__)
CORS(app) # Importante para que el index.html no dé error

# --- CONFIGURACIÓN ---
RPC_URL = os.getenv('RPC_URL', 'https://bsc-dataseed.binance.org/')
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Direcciones y Llaves
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
# Asegúrate que CONTRACT_ADDRESS en Render sea: 0xf74c6721970CA2735401F78476327a3d8867e73b
CONTRATO_TOKEN = os.getenv('CONTRACT_ADDRESS')
NODO_URL = os.getenv('NODO_MAESTRO_URL', 'https://binance-bot-hna7.onrender.com')

# ABI para emitir BCHC (Función mint)
ABI_TOKEN = [{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"}]

@app.route('/')
def home():
    try:
        # Esto es lo que lee tu index.html para mostrar el número real
        response = requests.get(f"{NODO_URL}/cadena")
        cadena = response.json()
        total_chc = sum(float(bloque['transacciones'][0]['monto']) for bloque in cadena if bloque['transacciones'])
        return jsonify({"suministro_global": total_chc, "status": "online"}), 200
    except:
        return jsonify({"suministro_global": 370460.0, "status": "error_lectura_cadena"}), 200

@app.route('/canjear', methods=['POST'])
def canjear():
    try:
        datos = request.json
        user_wallet = datos.get('wallet')
        cantidad = float(datos.get('cantidad'))

        if not PRIVATE_KEY or not CONTRATO_TOKEN:
            return jsonify({"error": "Faltan variables en Render"}), 500

        cuenta = w3.eth.account.from_key(PRIVATE_KEY)
        
        # Preparar la transacción de MINT (crear los BCHC)
        contract = w3.eth.contract(address=w3.to_checksum_address(CONTRATO_TOKEN), abi=ABI_TOKEN)
        monto_wei = w3.to_wei(cantidad, 'ether')
        
        tx = contract.functions.mint(user_wallet, monto_wei).build_transaction({
            'chainId': 56,
            'gas': 100000,
            'gasPrice': w3.to_wei('3', 'gwei'),
            'nonce': w3.eth.get_transaction_count(cuenta.address),
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction if hasattr(signed_tx, 'raw_transaction') else signed_tx.rawTransaction)

        return jsonify({
            "status": "Exito",
            "tx_hash": w3.to_hex(tx_hash),
            "mensaje": f"Enviados {cantidad} BCHC a {user_wallet}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
