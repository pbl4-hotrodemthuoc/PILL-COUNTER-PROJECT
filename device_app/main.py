import cv2
from ai_processor import AIProcessor
from picamera2 import Picamera2

def main():
    # 1. Khoi tao bo xu ly AI
    processor = AIProcessor()

    # 2. Khoi tao Picamera2
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (640, 480)
    picam2.preview_configuration.main.format = "BGR888"
    picam2.configure("preview")
    picam2.start()

    print("Camera da san sang. Nhan 'q' tren cua so video de thoat.")

    # 3. Vong lap xu ly real-time
    while True:
        # Lay frame tu camera
        frame = picam2.capture_array()

        # Xu ly frame bang AI
        _, result_image = processor.process_frame(frame)

        # Hien thi ket qua
        cv2.imshow("Real-time Pill Counter (Nhan 'q' de thoat)", result_image)

        # Thoat khi nhan 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("Dang dong chuong trinh...")
    picam2.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()