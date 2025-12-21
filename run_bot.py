#!/usr/bin/env python3
import os
import sys
import signal
import subprocess


def kill_existing_processes():
    """Убивает все существующие процессы python с этим ботом"""
    try:
        if sys.platform == "win32":
            # Windows
            subprocess.run(["taskkill", "/f", "/im", "python.exe"],
                           capture_output=True)
        else:
            # Linux/Mac
            subprocess.run(["pkill", "-f", "python.*main.py"],
                           capture_output=True)
            subprocess.run(["pkill", "-f", "python.*bot"],
                           capture_output=True)
    except Exception as e:
        print(f"Ошибка при остановке процессов: {e}")


def signal_handler(sig, frame):
    print("\nПолучен сигнал завершения, останавливаю бота...")
    sys.exit(0)


if __name__ == "__main__":
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Убиваем старые процессы
    print("Останавливаю старые процессы бота...")
    kill_existing_processes()

    # Запускаем бота
    print("Запускаю бота...")
    os.system("python main.py")