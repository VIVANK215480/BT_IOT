from flask import Flask, jsonify
import sqlite3
import datetime
import statistics
import websockets  # Thêm thư viện websockets
from sense_emu import SenseHat  # Thêm sense_emu để mô phỏng giá trị nhiệt độ

# Cấu hình socket (nếu dùng Node.js)
HOST = '192.168.190.130'  # Địa chỉ IP của server Node.js
PORT = 65432  # Port của server Node.js

app = Flask(__name__)
sense = SenseHat()  # Khởi tạo SenseHat
temperatures = []  # Danh sách lưu trữ nhiệt độ để tính T_lọc
n = 5  # Số lượng mẫu để tính T_lọc (tham số lịch sử)


# Kết nối đến SQLite
conn = sqlite3.connect('temperature.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS temperature (id INTEGER PRIMARY KEY AUTOINCREMENT, value REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()
conn.close()


async def send_websocket_data(t_avg, t_median):
    async with websockets.connect(f"ws://{HOST}:{PORT}") as websocket:
        data = f"{t_avg},{t_median}"
        await websocket.send(data)


@app.route('/temperature', methods=['GET'])
def get_temperature():
    temperature = round(sense.temperature, 2)  # Lấy giá trị nhiệt độ từ SenseHat
    if temperature is not None:
        temperatures.append(temperature)
        if len(temperatures) > n:
            temperatures.pop(0)

        t_avg = statistics.mean(temperatures) if temperatures else 0
        t_median = statistics.median(temperatures) if temperatures else 0

        conn = sqlite3.connect('temperature.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO temperature (value) VALUES (?)", (temperature,))
        conn.commit()
        conn.close()

        # Gửi dữ liệu qua WebSocket cho Node.js
        print(f"Data to send: t_avg={t_avg}, t_median={t_median}")
        try:
            await send_websocket_data(t_avg, t_median)
        except Exception as e:
            print(f"Lỗi WebSocket: {e}")

        return jsonify({'temperature': temperature, 't_avg': t_avg, 't_median': t_median, 'timestamp': datetime.datetime.now()})
    else:
        return jsonify({'error': 'Failed to get reading'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6007)
