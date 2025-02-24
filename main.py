import serial
import argparse
import time

def calc_crc(buf: bytes) -> int:
    """
    指定されたアルゴリズムでCRC16を計算します。（Cコード相当）
    """
    crc = 0xFFFF
    for b in buf:
        crc ^= b
        for _ in range(8):
            carryFlag = crc & 1
            crc >>= 1
            if carryFlag:
                crc ^= 0xA001
    return crc

def main():
    parser = argparse.ArgumentParser(
        description="8バイトのパケットをシリアルポートから受信し、\n"
                    "・生データ（16進数表記）を表示\n"
                    "・CRC16計算結果が0x0000なら先頭6バイトを2つの符号付き整数（big-endian）としてデコードし表示\n"
                    "・1秒あたりの成功パケット数をカウント\n"
                    "受信バッファ内のデータがずれている場合は、正しいパケット開始位置に合わせてスライドします。"
    )
    parser.add_argument(
        '--port',
        required=True,
        help="シリアルポート名 (例: COM3 または /dev/ttyUSB0)"
    )
    parser.add_argument(
        '--baudrate',
        type=int,
        default=115200,
        help="ボーレート (例: 9600)"
    )
    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baudrate, timeout=1)
        print(f"{args.port} を {args.baudrate} ボーでオープンしました")
    except Exception as e:
        print("シリアルポートのオープンに失敗しました:", e)
        return

    buffer = bytearray()
    packet_count = 0
    last_time = time.time()

    try:
        while True:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                buffer.extend(data)

                while len(buffer) >= 8:
                    packet = buffer[0:8]
                    crc_result = calc_crc(packet)

                    if crc_result == 0:
                        raw_hex = ' '.join(f"{b:02X}" for b in packet)
                        #print(f"Raw Data: {raw_hex}")

                        # 先頭6バイトのデータ部をbig-endianで符号付き整数に変換
                        data_part = packet[:6]
                        int1 = int.from_bytes(data_part[0:3], byteorder='big', signed=True)
                        int2 = int.from_bytes(data_part[3:6], byteorder='big', signed=True)
                        print(f"Torque: {int1/1000} [Nm], Speed: {int2/10} [rpm]")
                        #print(f"全8バイトの計算CRC16: 0x{crc_result:04X}  → CRC検証成功")
                        #print("-" * 40)

                        # 正しいパケットをカウント
                        packet_count += 1

                        # バッファから8バイトを削除
                        del buffer[:8]
                    else:
                        # 先頭の1バイトを削除して再同期
                        del buffer[0]

            # 1秒ごとにパケット数を表示
            current_time = time.time()
            if current_time - last_time >= 1.0:
                print(f"1秒あたりの成功パケット数: {packet_count} packets/sec")
                packet_count = 0
                last_time = current_time

    except KeyboardInterrupt:
        print("\nプログラムを終了します")
    except Exception as e:
        print("エラーが発生しました:", e)
    finally:
        ser.close()

if __name__ == '__main__':
    main()
