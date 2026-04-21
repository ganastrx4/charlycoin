from flask import Flask, jsonify
import requests
from web3 import Web3
import os

app = Flask(__name__)

# Configuración desde variables de entorno
w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
MI_BILLETERA = w3.eth.account.from_key(PRIVATE_KEY).address
CONTRATO_POOL = os.getenv('CONTRACT_ADDRESS')
NODO_URL = os.getenv('NODO_MAESTRO_URL')

# ABI resumido del contrato que hicimos (solo la función necesaria)
ABI_MINIMO = [{"inputs":[{"internalType":"uint256","name":"_total","type":"uint256"}],"name":"sincronizarMineria","outputs":[],"stateMutability":"nonpayable","type":"function"}]

@app.route('/sincronizar-ahora', methods=['GET'])
def sincronizar():
    try:
        # 1. Leer el CharlyScan (tu otro servicio)
        response = requests.get(f"{NODO_URL}/cadena")
        cadena = response.json()
        
        # 2. Calcular el total supply (sumando todos los bloques)
        total_chc = sum(float(bloque['transacciones'][0]['monto']) for bloque in cadena if bloque['transacciones'])

        # 3. Enviar a la Blockchain de Binance
        contract = w3.eth.contract(address=CONTRATO_POOL, abi=ABI_MINIMO)
        nonce = w3.eth.get_transaction_count(MI_BILLETERA)
        
        tx = contract.functions.sincronizarMineria(int(total_chc)).build_transaction({
            'chainId': 56, # BSC Mainnet
            'gas': 80000,
            'gasPrice': w3.to_wei('3', 'gwei'),
            'nonce': nonce,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return jsonify({
            "status": "Sincronizado",
            "total_chc": total_chc,
            "tx_hash": w3.to_hex(tx_hash)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
