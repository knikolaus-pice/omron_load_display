# Omron Serial Data Test Script V2
# Kevin Nikolaus
# November 21st, 2024

# Here is my test script to try and parse out values from the omron load display

# References
# https://assets.omron.eu/downloads/latest/manual/en/n128_k3hb-s_-x_-v_-h_digital_indicators_users_manual_en.pdf?v=7
# https://assets.omron.eu/downloads/latest/manual/en/n129_k3hb_communications_manual_en.pdf?v=5

import serial
import time

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
            #print("Sent frame (hex):", frame.hex())
            #print("Sent frame (ASCII):", frame.decode('ascii', errors='ignore'))

            # Wait for a response
            time.sleep(.1)
        else:
            raw_response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            #print("Raw Response:", raw_response)
            try:
                # Step 1: Validate and clean the response
                cleaned_response = validate_and_clean_response(raw_response)
                #print("Cleaned Response:", cleaned_response)

                # Step 2: Extract the data section
                data_section = extract_data_section(cleaned_response)
                display_value = int(data_section, 16) / 10  # Assuming the decimal point is implied at one decimal place
                #print("Extracted Data Section:", data_section)
                print("DISPLAY:", display_value) 
                
            except ValueError as e:
                print("Error decoding response:", e)
            time.sleep(.1)

except KeyboardInterrupt:
    print("Exiting...")
finally:
    ser.close()
