import importlib
from tokenize import Double
import pyautogui
import time
import os
import subprocess
import sys
import numpy as np
import cv2
package_name = "com.Sunborn.SnqxExilium"
import pyautogui as pag
import time
import random
from PIL import Image
import io
'''更新日志
9.28：确定可以用了
9.29：给点击的位置和间隔增加了波动

'''

# 获取当前脚本或打包后的 exe 所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 拼接 adb 可执行文件的路径
adb_path = os.path.join(script_dir, "adb", "adb.exe")

def get_connected_devices():
    """
    获取当前连接的设备（包括模拟器和实际设备）
    :return: 已连接的设备列表
    """
    result = subprocess.run([adb_path, "devices"], capture_output=True, text=True)
    devices = []
    for line in result.stdout.splitlines():
        if "device" in line and not line.startswith("List"):
            devices.append(line.split()[0])
    return devices

def list_connected_devices():
    """
    列出当前连接的所有设备和模拟器
    """
    devices = get_connected_devices()
    if devices:
        print("当前已连接的设备或模拟器：")
        for device in devices:
            print(f"设备: {device}")
    else:
        print("未检测到任何设备或模拟器。")
    
# 调用函数列出当前已连接的设备或模拟器
list_connected_devices()



def adb_screenshot():
    """
    使用 adb 获取当前连接的设备的屏幕截图并直接在内存中处理。
    :return: OpenCV 图像对象或错误信息
    """
    # 获取当前所有设备
    devices = get_connected_devices()

    if not devices:
        raise Exception("没有找到任何设备或模拟器")

    # 使用第一个检测到的设备
    target_device = devices[0]

    # 构建 adb 命令
    command = [adb_path, '-s', target_device, 'exec-out', 'screencap', '-p']

    try:
        # 执行 adb 命令获取截图数据
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        # 检查是否有错误输出
        if result.stderr:
            print(f"ADB 错误: {result.stderr.decode('utf-8')}")

        # 将图像数据加载为 NumPy 数组
        img_array = np.frombuffer(result.stdout, dtype=np.uint8)

        # 使用 OpenCV 将图像解码为 BGR 格式
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # 如果解码失败，抛出异常
        if img is None:
            raise Exception("无法从 adb 获取截图")

        return img

    except subprocess.CalledProcessError as e:
        print(f"ADB 命令执行失败: {e}")
        return None


def hex_to_rgb(hex_color):
    """将16进制颜色值转换为RGB"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

def is_color_similar(color1, color2, threshold):
    """
    比较两个RGB颜色是否相似，允许一定的阈值
    使用欧几里得距离来计算两个颜色之间的差异。
    """
    diff = np.linalg.norm(np.array(color1) - np.array(color2))  # 计算颜色差异
    return diff <= threshold

def check_color_range(x_start, y_start, x_end, y_end, colors, similarity_threshold=98):
    """
    在指定的坐标范围内检测是否存在指定的颜色（颜色可以有多个）。
    """
    # 获取屏幕截图，截图为 OpenCV 图像格式（BGR）
    screenshot = adb_screenshot()

    # 将阈值从百分比转换为适用于颜色空间的数值范围（0-255的颜色空间）
    # 如果阈值太小，尤其是对于浅色，可能不够灵敏，可以放宽阈值
    threshold = (100 - similarity_threshold) * 4  # 调整这个阈值来更适应颜色范围

    # 将颜色的16进制值转换为RGB值
    target_colors = [hex_to_rgb(color) for color in colors]

    # 遍历指定的坐标范围
    for y in range(y_start, y_end + 1):
        for x in range(x_start, x_end + 1):
            # OpenCV 图像是 BGR 格式，故此处将其转换为 RGB
            pixel_color = screenshot[y, x][::-1]  # 转换为 RGB 格式
            for target_color in target_colors:
                if is_color_similar(pixel_color, target_color, threshold):
                    return True  # 找到匹配的颜色

    return False


def shibie(x_start, y_start, x_end, y_end, colors, similarity_threshold=95, interval=1):
    """
    :param interval: 每次查找之间的时间间隔（秒）
    """
    print("未找到颜色，继续查找...")
    cs = 1
    while True:
        found = check_color_range(x_start, y_start, x_end, y_end, colors, similarity_threshold)
        cs += 1
        if found:
            print("找到指定颜色，退出循环")
            break
        sleep(1)
        if cs == 1:
            print("实在找不到，关闭脚本")
            print(f"未能找到目标颜色: {colors}")
            break
        #time.sleep(interval)  # 每次查找之间等待一段时间


def run_app(package_name):
    subprocess.run([adb_path, 'shell', 'monkey', '-p', package_name, '-c', 'android.intent.category.LAUNCHER', '1'], check=True)

def stop_app(package_name):
    subprocess.run([adb_path, 'shell', 'am', 'force-stop', package_name], check=True)

def close_all_apps():
    """
    关闭当前模拟器上运行的所有应用程序。
    """
    # 获取当前连接的设备列表
    devices = get_connected_devices()
    if not devices:
        print("没有找到任何设备或模拟器")
        return

    # 使用第一个检测到的设备
    target_device = devices[0]

    # 获取正在运行的应用列表
    command = [adb_path, '-s', target_device, 'shell', 'pm', 'list', 'packages', '-3']
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True)

    # 检查是否有运行中的应用
    if not result.stdout.strip():
        print("当前没有运行的应用")
        return

    # 获取所有应用包名
    packages = [line.split(":")[1] for line in result.stdout.strip().splitlines()]

    # 关闭每个应用
    for package in packages:
        print(f"正在关闭应用: {package}")
        subprocess.run([adb_path, '-s', target_device, 'shell', 'am', 'force-stop', package], check=True)

    print("所有应用已关闭")


import random

def sleep(x):
    time.sleep(x)

def tap(x, y):

    rand_x = x + random.randint(-15, 15)
    rand_y = y + random.randint(-10, 10)
    
    # 修改为使用 adb_path 进行调用
    subprocess.run([adb_path, 'shell', 'input', 'tap', str(rand_x), str(rand_y)], check=True)

    time.sleep(random.uniform(1.5, 2.5))

def double_tap(x, y):
    """
    模拟在指定坐标双击。
    """
    tap(x, y)
    sleep(2)
    tap(x, y)


def jzdj(x,y):
    # 修改为使用 adb_path 进行调用
    subprocess.run([adb_path, 'shell', 'input', 'tap', str(x), str(y)], check=True)
    time.sleep(random.uniform(1.5, 2.5))

def jzsj(x, y):
    """
    模拟在指定坐标双击。
    """
    jzdj(x, y)
    sleep(2)
    jzdj(x, y)



def swipe(x1, y1, x2, y2, duration=500):
    """
    使用ADB命令在指定坐标之间滑动
    duration以毫秒为单位，默认500ms
    """
    subprocess.run([adb_path, 'shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)], check=True)
    time.sleep(random.uniform(2, 3))



# 示例颜色范围检测的配置
ksyx = {
    'x_start': 577,
    'y_start': 599,
    'x_end': 584,
    'y_end': 612,
    'colors': ["#C5C5C5", "#8E8F8F"],
    'similarity_threshold': 95
}

def check_ksyx():
    """检查是否符合ksyx的颜色范围和相似度要求"""
    return check_color_range(
        ksyx['x_start'], 
        ksyx['y_start'], 
        ksyx['x_end'], 
        ksyx['y_end'], 
        ksyx['colors'], 
        ksyx['similarity_threshold']
    )

# 主要任务函数
def check_area(area):
    """
    封装颜色检测，减少重复代码。
    area: 一个字典，包含x_start, y_start, x_end, y_end, colors, similarity_threshold。
    """
    return check_color_range(
        area['x_start'], 
        area['y_start'], 
        area['x_end'], 
        area['y_end'], 
        area['colors'], 
        area['similarity_threshold']
    )



def tap_and_check_color(x, y, color_bounds, interval=1):
    """
    点击指定的坐标并检查颜色，如果未找到颜色，则继续点击并循环检测。

    :param x: 点击的 x 坐标
    :param y: 点击的 y 坐标
    :param color_bounds: 一个字典，包含颜色检测区域的坐标和颜色信息
    :param interval: 每次点击与检查之间的时间间隔（秒）
    """
    print("未找到颜色，继续点击和查找")
    while True:
        # 点击操作
        tap(x, y)
        time.sleep(interval)  # 等待一段时间

        # 检查颜色是否匹配
        found = check_color_range(**color_bounds)

        if found:
            print(f"找到颜色，退出循环")
            break
        
        time.sleep(interval)


zfzjm = {'x_start': 1199,'y_start': 122,'x_end': 1208,'y_end': 132,'colors': ["#2C2B29", "#A04C24"],'similarity_threshold': 97}
rwwc = {'x_start': 1100,'y_start': 94,'x_end': 1103,'y_end': 98,'colors': ["#EEEEEE"],'similarity_threshold': 97}
def zjm():
    while True:
        sbzjm = check_color_range(**zfzjm)
        if sbzjm:
            sbzjm = check_color_range(**zfzjm)
            time.sleep(3)
            if sbzjm:
                break

def ddzjm():
    sbzjm = check_color_range(**zfzjm)
    zdzjm = False
    if sbzjm:
        sbzjm = check_color_range(**zfzjm)
        time.sleep(3)
        return zdzjm == True



def qdzf():
    # 启动应用
    run_app("com.Sunborn.SnqxExilium")
    time.sleep(5)

    print("等待开始游戏")

    # 等待开始游戏的图像
    ksyx = {
        'x_start': 577,
        'y_start': 599,
        'x_end': 584,
        'y_end': 612,
        'colors': ["#C5C5C5", "#8E8F8F"],
        'similarity_threshold': 95
    }

    ddcs = 0
    while True:
        ddcs+=1
        sbzjm = check_color_range(**zfzjm)
        if sbzjm:
            sbzjm = check_color_range(**zfzjm)
            time.sleep(3)
            if sbzjm:
                break
        
        tap(650, 540)  # 模拟点击
        sbksyx = check_color_range(
            ksyx['x_start'], 
            ksyx['y_start'], 
            ksyx['x_end'], 
            ksyx['y_end'], 
            ksyx['colors'], 
            ksyx['similarity_threshold']
        )
        if sbksyx:  # 如果检测到开始游戏按钮
            break
        if ddcs==30:
            cqzf()
    print("开始游戏")
    time.sleep(20)
    ddcs=0
    # 检查是否需要更新
    gxjd = {
        'x_start': 329,
        'y_start': 616,
        'x_end': 335,
        'y_end': 623,
        'colors': ["#C9C8CE"],
        'similarity_threshold': 95
    }
    gxwc = {
        'x_start': 519,
        'y_start': 525,
        'x_end': 530,
        'y_end': 536,
        'colors': ["#415259", "#F2B118"],
        'similarity_threshold': 90
    }

    jcgx = check_color_range(
        gxjd['x_start'], 
        gxjd['y_start'], 
        gxjd['x_end'], 
        gxjd['y_end'], 
        gxjd['colors'], 
        gxjd['similarity_threshold']
    )

    if jcgx:  # 如果需要更新
        print("需要更新")
        tap(650, 550)  # 点击更新按钮
        time.sleep(30)
        while True:
            time.sleep(30) 
            if check_color_range(519, 525, 530, 536, ["#415259", "#F2B118"], similarity_threshold=95):
                break

    tap(600, 500)  # 点击继续按钮
    time.sleep(3)

    print("登录")

    # 等待主界面加载
    while True:
        ddcs+=1
        if ddcs==30:
            cqzf()
        sbzjm = check_color_range(**zfzjm)
        if sbzjm:
            sbzjm = check_color_range(**zfzjm)
            time.sleep(3)
            if sbzjm:
                break
        tap(1180, 80) 
        time.sleep(3)
        sbzjm = check_color_range(**zfzjm)
        if sbzjm:
            sbzjm = check_color_range(**zfzjm)
            time.sleep(3)
            if sbzjm:
                break
        
        tap(40, 40)  # 点击返回按钮
        time.sleep(3)
        sbzjm = check_color_range(**zfzjm)
        if sbzjm:
            sbzjm = check_color_range(**zfzjm)
            time.sleep(3)
            if sbzjm:
                break

    print("主界面已加载")
    time.sleep(3)


def cqzf():
    """
    强制关闭并重新启动应用
    """
    stop_app("com.Sunborn.SnqxExilium")
    stop_app("am force-stop com.android.browser")
    qdzf()

def qbbj():
    """
    体力补给逻辑
    """
    tap(750, 640)
    time.sleep(1)
    x = 125
    meiling = {
        'x_start': 811,
        'y_start': 464,
        'x_end': 858,
        'y_end': 503,
        'colors': ["#4E2A22", "#17BFD3"],
        'similarity_threshold': 95
    }
    while True:
        tap(200, x)
        x += 50
        time.sleep(1)
        mei1 = check_color_range(
            meiling['x_start'], 
            meiling['y_start'], 
            meiling['x_end'], 
            meiling['y_end'], 
            meiling['colors'], 
            meiling['similarity_threshold']
        )
        if mei1 or x >= 600:
            break
    
    if mei1:
        print("体力补给")
        double_tap(830, 570)
        double_tap(1130, 570)
    tap(1230, 50)
    time.sleep(2)


# 调用qdzf和qbbj
# 使用线程运行 UI 和主逻辑

# 创建一个 GUI 来选择 qz 的选项
import tkinter as tk
import sys
import json
import os

# 文件路径，用于保存和读取用户的选择
config_file = "qz_config.json"

def save_selection(selected_option):
    """保存用户的选择到配置文件"""
    with open(config_file, 'w') as f:
        json.dump({"qz": selected_option}, f)

def load_selection():
    """从配置文件中读取上次的选择"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            data = json.load(f)
            return data.get("qz", "突击与喷")  # 默认返回 "突击与喷"
    return "突击与喷"  # 默认选项

def create_ui():
    def on_submit():
        global qz_value
        selected_option = qz_var.get()
        # 保存用户选择的选项
        save_selection(selected_option)
        if selected_option == "突击与喷":
            qz_value = 1
        elif selected_option == "冲锋与机":
            qz_value = 2
        elif selected_option == "狙和刀":
            qz_value = 3
        elif selected_option == "手枪":
            qz_value = 4
        elif selected_option == "角色经验":
            qz_value = 5
        elif selected_option == "武器经验":
            qz_value = 6
        root.quit()  # 停止主循环
        root.destroy()  # 关闭窗口，但不结束脚本

    def on_close():
        print("窗口已关闭，脚本停止")
        root.quit()  # 停止主循环
        root.destroy()  # 关闭窗口
        exit()  # 停止脚本运行

    def auto_submit():
        """自动提交的回调函数"""
        print("10秒超时，自动提交当前选择")
        on_submit()  # 调用提交函数

    root = tk.Tk()
    root.title("选择刷取的配件种类")
    
    # 捕获关闭窗口事件
    root.protocol("WM_DELETE_WINDOW", on_close)
    
    # 从文件中加载上次的选择
    last_selection = load_selection()

    # 选项值
    qz_var = tk.StringVar(value=last_selection)  # 设置为上次的选择或默认值
    
    # 创建四个选项的单选按钮
    options = ["突击与喷", "冲锋与机", "狙和刀", "手枪","角色经验","武器经验"]
    for option in options:
        tk.Radiobutton(root, text=option, variable=qz_var, value=option).pack(anchor="w")
    
    # 提交按钮
    submit_button = tk.Button(root, text="提交", command=on_submit)
    submit_button.pack()
    
    # 设置 10 秒的自动提交定时器
    root.after(10000, auto_submit)  # 10000 毫秒后自动调用 auto_submit 函数
    
    # 启动 GUI
    root.mainloop()

def qingti():# 根据 qz 的选择执行不同的操作
    if qz_value == 1:
        tap(140, 230)
    elif qz_value == 2:
        tap(330, 230)
    elif qz_value == 3:
        tap(530, 230)
    elif qz_value == 4:
        tap(700, 230)
    else:
        tap(40,40)
        swipe(200, 400, 1000, 400, 500)
        if qz_value == 5:
            tap(170,400)
        elif qz_value == 6:
            tap(500,400)

    while True:
        tlbz = {'x_start': 1060, 'y_start': 590, 'x_end': 1080, 'y_end': 610, 'colors': ["#EF7942"], 'similarity_threshold': 90}
        tlbz1 = check_color_range(**tlbz)
        if tlbz1:
            tap(1220, 360)
            print("体力不足")
            break
        tap(900, 650)  # 自律
        zlcs = 0
        tl = {'x_start': 670, 'y_start': 440, 'x_end': 710, 'y_end': 520, 'colors': ["#FF5F40"], 'similarity_threshold': 95}
        tl1 = check_color_range(**tl)
        if qz_value in [1, 2, 3, 4]:
            print("配件")
            tap(900, 630)
        else:
            print("经验")
        
        while True:
            zlcs += 1
            if qz_value in [1, 2, 3, 4]:
                tap(940,440)
            elif qz_value in [5,6]:
                tap(860,390)
            tl1 = check_color_range(**tl)
            if tl1 or zlcs == 10:
                break
        if qz_value in [1, 2, 3, 4]:
            tap(340, 440)
        elif qz_value in [5,6]:
            tap(415,390)
        # 留 60 体力，使用 double_tap 
        if qz_value in [1, 2, 3, 4]:
            double_tap(820, 620)
            time.sleep(5)
            double_tap(820, 620)
        elif qz_value in [5,6]:
            double_tap(820, 550)
            time.sleep(5)
            double_tap(820, 550)


def houqin():
    print("后勤")
    tap(1170, 335)  # 后勤pq1
    tap(150, 300)  # 调度
    tap(1100, 550)  # 派遣
    tap(880, 630)  # 出发--同收益
    sleep(4)
    '''{137,528,142,530,"138,530,#EFEFEF",95}["#F26C1C"]{132,550,138,554,"135,552,#17859B",95}
    pqjl1 = {'x_start': 130,'y_start': 520,'x_end': 145,'y_end': 535,'colors': ["#EFEFEF"],'similarity_threshold': 80}
    pqjl2 = {'x_start': 230,'y_start': 520,'x_end': 245,'y_end': 535,'colors': ["#EFEFEF"],'similarity_threshold': 80}
    pqjl3 = {'x_start': 330,'y_start': 520,'x_end': 345,'y_end': 535,'colors': ["#EFEFEF"],'similarity_threshold': 80}
    pqjl4 = {'x_start': 430,'y_start': 520,'x_end': 440,'y_end': 535,'colors': ["#EFEFEF"],'similarity_threshold': 80}
    '''
    pqjl1 = {'x_start': 140, 'y_start': 520, 'x_end': 162, 'y_end': 536, 'colors': ["#F26C1C"], 'similarity_threshold': 80}
    pqjl2 = {'x_start': 240, 'y_start': 520, 'x_end': 262, 'y_end': 536, 'colors': ["#F26C1C"], 'similarity_threshold': 80}
    pqjl3 = {'x_start': 340, 'y_start': 520, 'x_end': 362, 'y_end': 536, 'colors': ["#F26C1C"], 'similarity_threshold': 80}
    pqjl4 = {'x_start': 430, 'y_start': 520, 'x_end': 462, 'y_end': 540, 'colors': ["#F26C1C"], 'similarity_threshold': 80}

    jl1 = check_color_range(**pqjl1)
    jl2 = check_color_range(**pqjl2)
    jl3 = check_color_range(**pqjl3)
    jl4 = check_color_range(**pqjl4)

    if jl1:
        double_tap(130, 550)
    if jl2:
        double_tap(230, 550)
    if jl3:
        double_tap(330, 550)
    if jl4:
        double_tap(430, 550)

    double_tap(940, 640)  # 收益
    tap(1110, 560)  # 拉满
    tap(780, 630)  # 取出
    tap(120, 210)  # 生产
    double_tap(980, 620)  # 取出

    time.sleep(2)
    double_tap(120, 40)
    time.sleep(4)


def dayueka():
    tap(650, 630)  # 大月卡
    dyk = {'x_start': 284, 'y_start': 278, 'x_end': 322, 'y_end': 300, 'colors': ["#D59B16", "#F0AF16"], 'similarity_threshold': 90}
    time.sleep(3)
    dyk1 = check_color_range(dyk['x_start'], dyk['y_start'], dyk['x_end'], dyk['y_end'], dyk['colors'], dyk['similarity_threshold'])

    if dyk1:
        double_tap(750, 36)  # 双击
        tap(1100, 660)  # 一键
        time.sleep(10)
        double_tap(540, 40)  # 双击
        tap(1140, 370)#一键
        tap(820, 570)#确定
        fxzg={842,232,860,254,"847,240,#4F7662|856,244,#DADBDE",95}
        while True:
            tap(900, 240)#好感
            tap(830, 575)#确定
            hxjs = {'x_start': 285, 'y_start': 277, 'x_end': 321, 'y_end': 302, 'colors': ["#F0AF16", "#D49B15"], 'similarity_threshold': 95}
            jshs = check_color_range(hxjs['x_start'], hxjs['y_start'], hxjs['x_end'], hxjs['y_end'], hxjs['colors'], hxjs['similarity_threshold'])
            if jshs:
                break
        tap(120, 40)
        time.sleep(5)

'''
def adb_screenshot():
    """使用ADB获取截图并返回为OpenCV格式的图像"""
    result = subprocess.run("adb exec-out screencap -p", shell=True, stdout=subprocess.PIPE)
    img = Image.open(io.BytesIO(result.stdout))  # 使用Pillow处理二进制流
    open_cv_image = np.array(img)  # 转换为OpenCV格式
    return cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

def hex_to_rgb(hex_color):
    """将16进制颜色值转换为RGB"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

def is_color_similar(color1, color2, threshold):
    """比较两个RGB颜色是否相似，允许一定的阈值"""
    diff = np.linalg.norm(np.array(color1) - np.array(color2))  # 计算颜色差异
    return diff <= threshold

def check_color_range(x_start, y_start, x_end, y_end, colors, similarity_threshold=95):
    """
    在指定的坐标范围内检测是否存在指定的颜色（颜色可以有多个）。
    """
    # 获取屏幕截图
    screenshot = adb_screenshot()

    # 将阈值从百分比转换为适用于颜色空间的数值范围（0-255的颜色空间）
    threshold = (100 - similarity_threshold) * 255 / 100

    # 将颜色的16进制值转换为RGB值
    target_colors = [hex_to_rgb(color) for color in colors]

    # 遍历指定的坐标范围
    for y in range(y_start, y_end + 1):
        for x in range(x_start, x_end + 1):
            pixel_color = screenshot[y, x]  # 获取当前像素的颜色
            for target_color in target_colors:
                if is_color_similar(pixel_color, target_color, threshold):
                    return True  # 找到匹配的颜色
    return False
'''


# 启动程序，显示 GUI 让用户选择配件

create_ui()
print("UI 已提交，继续脚本的其余部分")
#print(1)
qdzf()
cqzf()
if check_color_range(89,133,105,139,["#3A4A3E"], similarity_threshold=95):
    global yrd
    yrd = True
else:
    os.system('taskkill /F /PID %d' % os.getppid())
#qbbj()
tap(830, 630)  # 委托
time.sleep(5)
fscdl = False
if check_color_range(298,618,313,644,["#F0EFF3"], similarity_threshold=95):
    fscdl = False#print("首次登录")
else:
    fscdl = True    #print("非首次登录")
tap(120, 40)
houqin()

tap(1180, 80)
time.sleep(2)
tap(970, 40)

if fscdl:
    print("非首次登录")
    time.sleep(4)
    tap(1070, 400)  # 定向
    time.sleep(2)

    qingti()
    print("运行结束")
    stop_app("com.Sunborn.SnqxExilium")
    os.system('taskkill /F /PID %d' % os.getppid())
    

else:
    jzdj(1180, 50)  # 作战
    time.sleep(2)
    print("首次登录，去作战")
    swipe(200, 400, 1000, 400)
    time.sleep(5)
    tap(470, 400)  # 首领
    tap(980, 45)
    
    sltz = { 'x_start': 1119, 'y_start': 595, 'x_end': 1153, 'y_end': 610,'colors': ["#6F808A"],'similarity_threshold': 95}
    
    zy = check_color_range( sltz['x_start'],  sltz['y_start'], sltz['x_end'], sltz['y_end'], sltz['colors'],  sltz['similarity_threshold']  )
    #zy = False
    
    if zy:
        tap(850,650)
        tap(780,390)
        tap(800,550)
        time.sleep(3)
        tap(800,550)
    tap(200, 650)  #交易
    xdyy = { 'x_start': 417, 'y_start': 153,'x_end': 423,'y_end': 160,'colors': ["#450B23", "#C45B55"], 'similarity_threshold': 98 }
    #xdyy1 = check_color_range( xdyy['x_start'], xdyy['y_start'], xdyy['x_end'],  xdyy['y_end'], xdyy['colors'], xdyy['similarity_threshold'])
    xdyy1 = False
    if xdyy1:
        print("新的一月")
        time.sleep(3)
        for i in range(2):
            sleep(2)
            tap(400, 300)
            swipe(450,400,820, 395)
            double_tap(800, 550)
            time.sleep(2)
    #xdyy1 = True
    # 检查是否新的一周
    if zy:
        print("新的一周")
        pjx = {'x_start': 401, 'y_start': 154,'x_end': 407,'y_end': 159,'colors': ["#FE9425", "#F6C9B3"],'similarity_threshold': 95 }
        pjx1 = check_color_range(pjx['x_start'], pjx['y_start'], pjx['x_end'], pjx['y_end'],  pjx['colors'], pjx['similarity_threshold'])

        time.sleep(3)
        if not pjx1:
            for i in range(3):
                sleep(2)
                tap(400, 300)
                jzsj(820, 395)
                double_tap(800, 550)
                time.sleep(2)

    tap(40,40)
    if zy:
        tap(40,40)
        time.sleep(2)
        swipe(200, 400, 1000, 400, 1000)
        time.sleep(2)
        tap(1040, 400)
        time.sleep(2)
        tap(1000, 600)  # 领取
        double_tap(640, 600)  
        tap(1130, 80)
        tap(40, 40)
    else:
        time.sleep(2)
        tap(40, 40)


    swipe(200, 400, 1000, 400, 1000)
    time.sleep(2)

    # 点击操作，进入PVP
    tap(760, 350)
    print("pvp")
    time.sleep(10)

    if zy:
        double_tap(800, 400)
        double_tap(800, 400)
    double_tap(985,660)

    # 颜色范围定义结构，保持在一行
    gr1 = {'x_start': 99, 'y_start': 409, 'x_end': 105, 'y_end': 423, 'colors': ["#384B53"], 'similarity_threshold': 70}
    gr2 = {'x_start': 345, 'y_start': 409, 'x_end': 355, 'y_end': 423, 'colors': ["#384B53"], 'similarity_threshold': 70}
    gr3 = {'x_start': 595, 'y_start': 409, 'x_end': 605, 'y_end': 423, 'colors': ["#384B53"], 'similarity_threshold': 70}
    gr4 = {'x_start': 842, 'y_start': 409, 'x_end': 852, 'y_end': 423, 'colors': ["#384B53"], 'similarity_threshold': 70}
    gr5 = {'x_start': 1089, 'y_start': 409, 'x_end': 1099, 'y_end': 423, 'colors': ["#384B53"], 'similarity_threshold': 70}
    gr = {'x_start': 751, 'y_start': 647, 'x_end': 762, 'y_end': 663, 'colors': ["#DB9F30"], 'similarity_threshold': 80}

    cs = 1
    double_tap(1100,660)
    while cs < 3:
        time.sleep(2)
        print(f"第 {cs} 遍识别")
    
        sr1 = check_color_range(**gr1)
        sr2 = check_color_range(**gr2)
        sr3 = check_color_range(**gr3)
        sr4 = check_color_range(**gr4)
        sr5 = check_color_range(**gr5)
    
        if not sr1 and cs < 3:
            tap(100, 400)
            tap(1070,550)
            shibie(**gr)
            cs += 1
            print("打第一个")
            time.sleep(5)
            tap(600, 630)
            tap(820,550)
            time.sleep(5)
            tap(1084, 40)
            shibie(**rwwc)
            print("战斗胜利")
            tap(500, 600)
            time.sleep(5)
            double_tap(500, 600)
            time.sleep(5)
            double_tap(1000, 640)
            time.sleep(10)

        if not sr2 and cs < 3:
            tap(340, 400)
            tap(1070,550)
            shibie(**gr)
            cs += 1
            print("打第二个")
            time.sleep(5)
            tap(600, 630)
            tap(820,550)
            time.sleep(5)
            tap(1084, 40)
            shibie(**rwwc)
            print("战斗胜利")
            tap(500, 600)
            time.sleep(5)
            double_tap(500, 600)
            time.sleep(5)
            double_tap(1000, 640)
            time.sleep(10)

        if not sr3 and cs < 3:
            tap(600, 400)
            tap(1070,550)
            shibie(**gr)
            cs += 1
            print("打第三个")
            time.sleep(5)
            tap(600, 630)
            tap(820,550)
            time.sleep(5)
            tap(1084, 40)
            shibie(**rwwc)
            print("战斗胜利")
            tap(500, 600)
            time.sleep(5)
            double_tap(500, 600)
            time.sleep(5)
            double_tap(1000, 640)
            time.sleep(10)

        if not sr4 and cs < 3:
            tap(840, 400)
            tap(1070,550)
            shibie(**gr)
            cs += 1
            time.sleep(5)
            tap(600, 630)
            tap(820,550)
            time.sleep(5)
            tap(1084, 40)
            shibie(**rwwc)
            print("战斗胜利")
            tap(500, 600)
            time.sleep(5)
            double_tap(500, 600)
            time.sleep(5)
            double_tap(1000, 640)
            time.sleep(10)

        if not sr5 and cs < 3:
            tap(1100, 400)
            tap(1070,550)
            shibie(**gr)
            cs += 1
            time.sleep(5)
            tap(600, 630)
            tap(820,550)
            time.sleep(5)
            tap(1084, 40)
            shibie(**rwwc)
            print("战斗胜利")
            tap(500, 600)
            time.sleep(5)
            double_tap(500, 600)
            time.sleep(5)
            double_tap(1000, 640)
            time.sleep(10)

        tap(1182, 660)
        time.sleep(2)

    # 完成每日奖励任务
    tap(40, 40)
    double_tap(423, 640)  # 每日奖励
    tap(120, 40)
    time.sleep(5)
    tap(500, 640)
    tap(120, 40)
    time.sleep(5)  # sleep(5000)
    tap(500, 640)
    tap(120, 40)
    if zy:
        print("后勤商店")
        tap(1170, 335)  # 后勤pq1
        tap(150, 300)  # 调度
        tap(1100, 650)  # 商店
        sleep(2)
        tap(620, 430)
        jzsj(820, 395)
        double_tap(800, 550)
        time.sleep(2)
        tap(380, 620)
        jzsj(820, 395)
        double_tap(800, 550)
        time.sleep(2)
        tap(120, 40)
        time.sleep(5)  # sleep(5000)
    print("进入兵蚁")
    tap(90,530)
    tap(240, 500)  # 兵蚁
    time.sleep(5)
    tap(840, 147)  # 邮箱
    time.sleep(3)
    double_tap(270, 660)  # 领取
    tap(40, 40)
    tap(640, 140)  # 社区
    time.sleep(10)
    tap(390, 540)  # 签到
    tap(640, 700)
    tap(550, 540)
    double_tap(560, 620)
    double_tap(560, 620)
    double_tap(560, 620)
    stop_app("am force-stop com.android.browser")
    run_app("com.Sunborn.SnqxExilium")
    time.sleep(5)
    tap(370, 280)  # 仓库
    tap(100, 380)  # 武器配件
    tap(65, 660)  # 拆解

    # 选拆解品质部分（注释掉的部分）
    # tap(580, 500)  # 选拆解品质
    # tap(530, 400)  # 紫色
    # tap(740, 500)
    # tap(1000, 660)

    time.sleep(5)
    tap(740, 500)
    tap(60, 500)  # 筛选
    tap(640, 210)  # 生命
    tap(770, 210)  # 防御
    tap(800, 600)  # 确定
    tap(580, 500)  # 选拆解品质
    tap(536, 450)  # 金色
    tap(740, 500)
    tap(1000, 660)
    time.sleep(5)
    tap(740, 500)
    tap(60, 500)  # 筛选
    tap(640, 210)  # 生命
    tap(770, 210)  # 防御
    tap(640, 270)  # 生命
    tap(770, 270)  # 防御
    tap(800, 600)  # 确定
    tap(740, 500)
    tap(1000, 660)
    time.sleep(5)
    tap(740, 500)
    tap(120, 40)
    time.sleep(5)
    # 这里是清体力
    tap(1110, 90)
    time.sleep(4)
    tap(960, 40)
    time.sleep(2)
    tap(1255, 440)  # 钱
    time.sleep(2)
    tap(900, 650)
    time.sleep(2)
    jzdj(775,390)
    jzdj(780,390)
    # 拉满
    time.sleep(2)
    double_tap(800, 550)
    time.sleep(5)
    double_tap(800, 550)
    tap(40, 40)
    tap(900, 400)  # 定向
    time.sleep(2)

    qingti()
    
    tap(120, 40)  # 点击返回
    time.sleep(5)
    tap(830, 630)  # 每日委托
    tap(1080, 640)  # 双击
    time.sleep(2)
    double_tap(180, 630)  # 双击
    tap(1100, 200)  # 点击操作
    time.sleep(5)
    tap(40, 40)  # 点击返回
    tap(1100, 200)  # 再次点击
    sleep(2)
    tap(120, 40)  # 点击返回
    time.sleep(5)
    tap(1180, 480)  # 商店
    sleep(2)
    tap(120, 320)
    tap(1050, 120)
    tap(400, 360)
    tap(800, 550)
    time.sleep(2)
    tap(600, 600)
    time.sleep(2)
    if xdyy1:  #新的一月
        tap(90, 565)
        tap(590, 120)
        for i in range(3):
            sleep(2)
            tap(400, 300)
            jzsj(820, 400)
            double_tap(800, 550)
            time.sleep(2)
    tap(120, 40)  # 返回
    time.sleep(3)

    bz={'x_start': 979, 'y_start': 123, 'x_end': 1003, 'y_end': 162, 'colors': ["#FFCF7D","#9C6941"], 'similarity_threshold': 95}
    
    tap(920, 630)  # 班组
    time.sleep(5)
    ybz=check_color_range(bz['x_start'], bz['y_start'], bz['x_end'], bz['y_end'], bz['colors'], bz['similarity_threshold'])
    if ybz:
        double_tap(890, 650)  # 双击，要务
        tap(1035, 620)  # 开始
        time.sleep(15)
        tap(600, 630)  # 开战
        tap(820,550)
        time.sleep(10)

        zdzd = {'x_start': 1081, 'y_start': 29, 'x_end': 1087, 'y_end': 32, 'colors': ["#C8C8C8"], 'similarity_threshold': 95}
    
        while True:
            zdzd1 = check_color_range(zdzd['x_start'], zdzd['y_start'], zdzd['x_end'], zdzd['y_end'], zdzd['colors'], zdzd['similarity_threshold'])
            if zdzd1:
                tap(1085, 35)  # 自动战斗
            time.sleep(5)
            rwwc1 = check_color_range(rwwc['x_start'], rwwc['y_start'], rwwc['x_end'], rwwc['y_end'], rwwc['colors'], rwwc['similarity_threshold'])
            if rwwc1:
                break
        print("战斗胜利")
        double_tap(500, 640)  # 双击
        time.sleep(5)
        double_tap(1000, 640)  # 双击
        time.sleep(5)
        tap_and_check_color(1180,110,bz)
        tap(777, 649)  # 补给
        tap(1100, 630)
        time.sleep(3)
        tap(1100, 630)

    tap(120, 40)  # 返回
    time.sleep(3)

    dayueka()

    if yrd:    
        tap(180, 115)  # 活动
        print("活动")
        time.sleep(2)
        double_tap(1040, 640)  # 元日点下，双击
        tap(1180, 670)
        swipe(1200, 200, 200, 200)  # 滑动操作
        tap(660, 350)
        tap(950, 660)
        jzdj(777, 390)#拉满
        tap(800, 550)
        time.sleep(5)
        tap(600, 550)
        double_tap(120, 40)  # 返回
        time.sleep(5)
    
    
    tap(920, 640)  # 班组
    time.sleep(3)
    tap(1100, 600)
    time.sleep(3)

    ghz = {'x_start': 1077, 'y_start': 596, 'x_end': 1091, 'y_end': 610, 'colors': ["#CDA532"], 'similarity_threshold': 95}
    ghz1 = check_color_range(ghz['x_start'], ghz['y_start'], ghz['x_end'], ghz['y_end'], ghz['colors'], ghz['similarity_threshold'])

    if ghz1:
        print("有工会战")
        os.system('taskkill /F /PID %d' % os.getppid())

    stop_app("com.Sunborn.SnqxExilium")
    os.system('taskkill /F /PID %d' % os.getppid())

    


