"""
机器码获取模块
用于获取当前机器的硬件信息并生成唯一机器码
"""

import platform
import hashlib
import subprocess
import re


def get_machine_info():
    """获取机器硬件信息"""
    machine_info = []
    
    system = platform.system()
    
    if system == "Windows":
        # Windows系统
        try:
            # 获取CPU序列号
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'ProcessorId'],
                capture_output=True,
                text=True,
                check=True
            )
            cpu_id = result.stdout.strip().split('\n')[1].strip()
            if cpu_id:
                machine_info.append(f"CPU:{cpu_id}")
        except:
            pass
        
        try:
            # 获取主板序列号
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'SerialNumber'],
                capture_output=True,
                text=True,
                check=True
            )
            motherboard_id = result.stdout.strip().split('\n')[1].strip()
            if motherboard_id and motherboard_id != "To be filled by O.E.M.":
                machine_info.append(f"MB:{motherboard_id}")
        except:
            pass
        
        try:
            # 获取MAC地址
            result = subprocess.run(
                ['getmac', '/fo', 'csv', '/nh'],
                capture_output=True,
                text=True,
                check=True
            )
            macs = re.findall(r'([0-9A-F]{2}[:-]){5}[0-9A-F]{2}', result.stdout, re.I)
            if macs:
                machine_info.append(f"MAC:{macs[0]}")
        except:
            pass
        
    elif system == "Linux":
        # Linux系统
        try:
            # 获取CPU ID
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'Serial' in line:
                        cpu_id = line.split(':')[1].strip()
                        if cpu_id:
                            machine_info.append(f"CPU:{cpu_id}")
                            break
        except:
            pass
        
        try:
            # 获取主板序列号
            result = subprocess.run(
                ['dmidecode', '-s', 'baseboard-serial-number'],
                capture_output=True,
                text=True,
                check=True
            )
            motherboard_id = result.stdout.strip()
            if motherboard_id and motherboard_id != "Not Specified":
                machine_info.append(f"MB:{motherboard_id}")
        except:
            pass
        
        try:
            # 获取MAC地址
            result = subprocess.run(
                ['ip', 'link', 'show'],
                capture_output=True,
                text=True,
                check=True
            )
            macs = re.findall(r'([0-9a-f]{2}[:-]){5}[0-9a-f]{2}', result.stdout, re.I)
            if macs:
                machine_info.append(f"MAC:{macs[0]}")
        except:
            pass
        
    elif system == "Darwin":  # macOS
        try:
            # 获取硬件UUID
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True,
                text=True,
                check=True
            )
            uuid_match = re.search(r'Hardware UUID:\s*([A-F0-9-]+)', result.stdout, re.I)
            if uuid_match:
                machine_info.append(f"UUID:{uuid_match.group(1)}")
        except:
            pass
    
    # 如果无法获取硬件信息，使用系统信息作为备选
    if not machine_info:
        machine_info.append(f"NODE:{platform.node()}")
        machine_info.append(f"SYSTEM:{platform.system()}")
        machine_info.append(f"PROCESSOR:{platform.processor()}")
    
    return machine_info


def get_machine_code():
    """
    生成机器码
    返回: 32位十六进制字符串
    """
    machine_info = get_machine_info()
    info_string = "|".join(machine_info)
    
    # 使用SHA256生成唯一机器码
    machine_code = hashlib.sha256(info_string.encode('utf-8')).hexdigest()[:32].upper()
    
    return machine_code


if __name__ == "__main__":
    # 测试获取机器码
    print("正在获取机器信息...")
    info = get_machine_info()
    print(f"机器信息: {info}")
    print(f"机器码: {get_machine_code()}")


