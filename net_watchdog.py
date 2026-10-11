import threading
import time
import subprocess
import urllib.request
import os
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
import psutil


TARGET_URL = "http://cp.cloudflare.com/generate_204"  
CHECK_INTERVAL = 15     
TIMEOUT = 10             
running = True          


ROUTER_SCRIPT_PATH = r"D:\Programs\Router\Router FireFox.py"


def check_internet():
    try:
        urllib.request.urlopen(TARGET_URL, timeout=TIMEOUT)
        return True
    except Exception:
        return False

def restart_network_stack(icon):
    icon.notify("TIMEOUT, перезагрузка стека...", title="Net Watchdog")
    subprocess.run("ipconfig /release", shell=True, stdout=subprocess.DEVNULL)
    subprocess.run("ipconfig /flushdns", shell=True, stdout=subprocess.DEVNULL)
    subprocess.run("ipconfig /renew", shell=True, stdout=subprocess.DEVNULL)
    time.sleep(5)


def watchdog_loop(icon):
    failed_strikes = 0
    countdown = CHECK_INTERVAL
    escalation_level = 0  
    

    history = []
    
 
    last_recv = psutil.net_io_counters().bytes_recv
    last_time = time.time()
    
    status_str = "Инициализация"
    loss_str = "0%"
    speed_str = "0.0 МБ/с"

    while running:
        time.sleep(1) 
        
     
        current_time = time.time()
        current_recv = psutil.net_io_counters().bytes_recv
        
        delta_bytes = current_recv - last_recv
        delta_time = current_time - last_time
        if delta_time <= 0: delta_time = 1
        
        speed_Bps = delta_bytes / delta_time  
        speed_KBps = speed_Bps / 1024         
        speed_MBps = speed_KBps / 1024         
        
        if speed_MBps < 1.0:
            speed_str = f"{int(speed_KBps)} КБ/с"
        else:
             speed_str = f"{speed_MBps:.1f} МБ/с"
            
        last_recv = current_recv
        last_time = current_time

        
        countdown -= 1
        
        
        if countdown <= 0:
            success = check_internet()
            
            history.append(success)
            if len(history) > 10:
                history.pop(0)
            
            loss_pct = (history.count(False) / len(history)) * 100
            loss_str = f"{int(loss_pct)}%"
            
            if success:
                failed_strikes = 0
                escalation_level = 0  
                status_str = "ОК"
            else:
                failed_strikes += 1
                status_str = f"ДРОП ({failed_strikes}/3)"
                
           
            if failed_strikes >= 3:
                if escalation_level == 0:
                    
                    status_str = "РЕСТАРТ СЕТИ..."
                    icon.title = f"Net Watchdog\nСтатус: {status_str}"
                    restart_network_stack(icon)
                    
                    failed_strikes = 0
                    history.clear()
                    loss_str = "0%"
                    escalation_level = 1  
                    status_str = "ОК (После сброса стека)"
                
                elif escalation_level == 1:
                    
                    status_str = "РЕСТАРТ РОУТЕРА..."
                    icon.title = f"Net Watchdog\nОжидание ребута (80с)..."
                    icon.notify("Стек не помог. Дергаю роутер через Selenium...", title="Net Watchdog")
                    
                    try:
                        
                        subprocess.run(f'python "{ROUTER_SCRIPT_PATH}"', shell=True, check=True)
                    except Exception as e:
                        icon.notify(f"Ошибка запуска Router.py: {e}", title="Net Watchdog")
                    
                    
                    time.sleep(80)
                    
                    
                    last_recv = psutil.net_io_counters().bytes_recv
                    last_time = time.time()
                    
                    failed_strikes = 0
                    history.clear()
                    loss_str = "0%"
                    escalation_level = 0  
                    status_str = "ОК (Роутер перезапущен)"
                
            countdown = CHECK_INTERVAL 

        
        icon.title = (
            f"Net Watchdog\n"
            f"Сеть: {status_str} (Потери: {loss_str})\n"
            f"Трафик ПК: {speed_str}\n"
            f"До проверки: {countdown}с"
        )

def create_default_icon():
    image = Image.new('RGB', (64, 64), color=(31, 31, 31))
    dc = ImageDraw.Draw(image)
    dc.ellipse((16, 16, 48, 48), fill=(0, 200, 100))
    return image

def on_exit(icon, item):
    global running
    running = False
    icon.stop()

def main():
    if os.path.exists("icon.ico"):
        icon_image = Image.open("icon.ico")
    else:
        icon_image = create_default_icon()

    icon = pystray.Icon(
        "NetWatchdog",
        icon_image,
        "Net Watchdog: Запуск...",
        menu=pystray.Menu(item('Выход', on_exit))
    )

    checker_thread = threading.Thread(target=watchdog_loop, args=(icon,), daemon=True)
    checker_thread.start()
    icon.run()

if __name__ == "__main__":
    main()