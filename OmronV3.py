# Omron Serial Data Test Script V2 
# Kevin Nikolaus
# November 21st, 2024

import serial
import time
import redis

# Redis connection
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Initialize the serial port
ser = serial.Serial(
    port='COM4',         # Replace with your COM port
    baudrate=9600,       # Baud rate
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1            # Timeout in seconds
)

def calculate_bcc(data):
    """Calculate the BCC (Block Check Character) for given data."""
    bcc = 0
    for byte in data:
        bcc ^= byte
    return bcc

def validate_and_clean_response(response):
    """
    Validate the response frame and clean extra trailing characters.

    Parameters:
        response (str): The raw response frame as a string.

    Returns:
        str: The cleaned response frame.
    """
    if not response or response[0] != '\x02':
        raise ValueError("Missing STX at the beginning of the frame.")
    if '\x03' not in response:
        raise ValueError("Missing ETX in the frame.")
    
    # Trim everything after the first ETX
    response = response[:response.index('\x03') + 1]
    return response

def extract_data_section(response):
    """
    Extract the data section from the response frame based on CompoWay/F structure.

    Parameters:
        response (str): The validated and cleaned response frame as a string.

    Returns:
        str: The extracted data section.
    """
    # Strip STX and ETX
    frame_body = response[1:-1]

    # Check minimum length of the response frame
    if len(frame_body) < 16:
        raise ValueError("Frame too short to extract data")

    # Extract sections based on the structure
    data_section = frame_body[13:]  # Data Section
    return data_section

def decode_signed_value(hex_value, bit_length=16):
    """
    Decode a hexadecimal value as a signed integer based on two's complement.

    Parameters:
        hex_value (str): The hexadecimal string representation of the value.
        bit_length (int): The bit length of the value (default is 16).

    Returns:
        int: The decoded signed integer value.
    """
    value = int(hex_value, 16)  # Convert hex to integer
    # Check if the value is negative in two's complement
    if value >= 2**(bit_length - 1):  # MSB is set
        value -= 2**bit_length
    return value

# Frame components
STX = 0x02  # Start of Text
ETX = 0x03  # End of Text
Node = "01"  # Node Number
SubAddress = "00"  # Sub-address (not used, set to "00")
ServiceID = "0"  # Service ID (not used, set to "0")
MRC = "01"  # Main Request Code
SRC = "01"  # Sub Request Code
Variable_Type = "C0"  # Variable Type
Address = "0002"  # Monitor values
Bit_Position = "00"  # Always 00 for K3HB
Number_of_Elements = "0001"  # Read one element
CommandText = Variable_Type + Address + Bit_Position + Number_of_Elements
data_ascii = Node + SubAddress + ServiceID + MRC + SRC + CommandText

# Main program loop
try:
    while True:
        if ser.in_waiting == 0:  # Check if there's no incoming data
            # Construct the frame
            frame = bytearray()
            frame.append(STX)
            frame.extend(data_ascii.encode('ascii'))  # Add ASCII data
            frame.append(ETX)

            # Calculate and append the BCC
            bcc = calculate_bcc(frame[1:])  # Calculate BCC (excluding STX)
            frame.append(bcc)

            # Send the frame
            ser.write(frame)

            # Wait for a response
            time.sleep(0.1)
        else:
            raw_response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            try:
                # Step 1: Validate and clean the response
                cleaned_response = validate_and_clean_response(raw_response)

                # Step 2: Extract the data section
                data_section = extract_data_section(cleaned_response)

                # Step 3: Decode the signed value
                decoded_value = decode_signed_value(data_section)  # Decode the signed integer
                display_value = decoded_value / 10  # Scale the value as per the decimal place
                
                # Step 4: Store in Redis
                redis_conn.set("load-cell", "{:.6f}".format(display_value))
                print("DISPLAY:", display_value)
                
            except ValueError as e:
                print("Error decoding response:", e)
            time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting...")
finally:
    ser.close()
