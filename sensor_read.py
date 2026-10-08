from sense_emu import SenseHat  # 注意模块名是 sense_emu，不是 sense_enu

sense = SenseHat()

# 正确的方法调用（使用 . 符号）
temperature = sense.get_temperature()
humidity = sense.get_humidity()
pressure = sense.get_pressure()

# 使用Python的print函数和f-string格式化输出
print(f"Temperature: {temperature:.1f}°C")
print(f"Humidity: {humidity:.1f}%")
print(f"Pressure: {pressure:.1f}hPa")
