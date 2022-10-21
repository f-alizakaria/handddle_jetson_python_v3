

def send_message(se, message):
    # Send the message to all connected STM32
    for port_name in se:
        for i in range(len(message)):
            se[port_name].write(message[i:i + 1])