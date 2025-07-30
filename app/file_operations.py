def text_to_binary(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        text = file.read()

    binary = ''.join(format(ord(char), '08b') for char in text)

    with open(output_file, 'w') as file:
        file.write(binary)
    

    print(f"Converted text to binary, length: {len(binary)} bits")

def binary_to_ascii(input_file_path, output_file_path):
    try:
        with open(input_file_path, 'r') as input_file:
            binary_content = input_file.read().strip() 

            # Make sure the binary length is a multiple of 8
            if len(binary_content) % 8 != 0:
                # Pad with zeros
                binary_content = binary_content + '0' * (8 - (len(binary_content) % 8))

            chunks = [binary_content[i:i+8] for i in range(0, len(binary_content), 8)]

            ascii_values = [int(chunk, 2) for chunk in chunks if chunk.strip()]

            with open(output_file_path, 'w') as output_file:
                for value in ascii_values:
                    output_file.write(f"{value}\n")

            print(f"Converted binary to ASCII, values: {len(ascii_values)}")
    except FileNotFoundError:
        print(f"Error: File '{input_file_path}' not found.")
    except Exception as e:
        print(f"Error in binary_to_ascii: {str(e)}")

def format_binary(value):
    binary_str = bin(value)[2:]  # Remove "0b" prefix
    return binary_str.zfill(8)  # Pad with leading zeros

def rgb_binary_de(input_file, output_file):
    try:
        with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
            data_list = []
        
            # Read all lines
            for line in f_in:
                line = line.strip()
                if line:  # Skip empty lines
                    data_list.append(line)
            
            print(f"Read {len(data_list)} RGB values for binary conversion")
            
            # Process data in smaller chunks
            chunk_size = 3000
            for i in range(0, len(data_list), chunk_size):
                chunk = data_list[i:i+chunk_size]
                process_rgb_data(chunk, f_out)
    
    except Exception as e:
        print(f"Error in rgb_binary_de: {str(e)}")
        # Create empty output file if processing fails
        open(output_file, 'w').close()

def process_rgb_data(data_list, output_file):
    # Group data into sets of 3 (RGB values)
    for i in range(0, len(data_list), 3):
        if i + 2 < len(data_list):  # Ensure we have all three RGB values
            try:
                r, g, b = map(int, data_list[i:i+3])
                binary_r = format_binary(r)
                binary_g = format_binary(g)
                binary_b = format_binary(b)
            
                output_file.write(f"{binary_r}\n{binary_g}\n{binary_b}\n")
            except ValueError as e:
                print(f"Error on line {i+1}: Invalid data ({e}). Skipping entry.")
        elif i + 1 < len(data_list):  # Handle the case where we have 2 values
            try:
                r, g = map(int, data_list[i:i+2])
                binary_r = format_binary(r)
                binary_g = format_binary(g)
                
                output_file.write(f"{binary_r}\n{binary_g}\n")
            except ValueError as e:
                print(f"Error on line {i+1}: Invalid data ({e}). Skipping entry.")
        elif i < len(data_list):  # Handle the case where we have 1 value
            try:
                r = int(data_list[i])
                binary_r = format_binary(r)
                
                output_file.write(f"{binary_r}\n")
            except ValueError as e:
                print(f"Error on line {i+1}: Invalid data ({e}). Skipping entry.")

def join_lines_with_space(input_file, output_file):
    try:
        with open(input_file, 'r') as file:
            lines = file.readlines()

        joined_text = ' '.join([line.strip() for line in lines if line.strip()])

        with open(output_file, 'w') as file:
            file.write(joined_text)
        
        print(f"Joined {len(lines)} lines with spaces, total length: {len(joined_text)}")
    
    except Exception as e:
        print(f"Error in join_lines_with_space: {str(e)}")
        # Create empty output file if processing fails
        open(output_file, 'w').close()

def de_bin_to_text(input_file, output_file):
    try:
        with open(input_file, 'r', encoding="utf-8") as file:
            binary_str = file.read().replace(' ', '')  

        print(f"Converting binary to text, binary length: {len(binary_str)}")
        
        # Ensure binary length is multiple of 8
        if len(binary_str) % 8 != 0:
            padding = '0' * (8 - (len(binary_str) % 8))
            binary_str += padding
            print(f"Padded binary with {len(padding)} zeros")
        
        # Process binary in chunks to handle large files
        text = ''
        for i in range(0, len(binary_str), 8):
            if i + 8 <= len(binary_str):
                byte = binary_str[i:i+8]
                if byte.strip() and set(byte) <= {'0', '1'}:  # Ensure valid binary
                    try:
                        text += chr(int(byte, 2))
                    except ValueError as e:
                        print(f"Invalid binary value: {byte}, error: {str(e)}")
        
        print(f"Converted binary to text, text length: {len(text)}")

        with open(output_file, 'w', encoding="utf-8") as file:
            file.write(text)
    
    except Exception as e:
        print(f"Error in de_bin_to_text: {str(e)}")
        # Create empty output file if processing fails
        open(output_file, 'w', encoding="utf-8").close()

def remove_last_letter(input_file, output_file):
    try:
        with open(input_file, 'r', encoding="utf-8") as file:
            content = file.read()

        print(f"Input content length before removing last letter: {len(content)}")
        
        # Remove the last character only if the content isn't empty
        if content:
            updated_content = content[:-1]
        else:
            updated_content = content
        
        print(f"Output content length after removing last letter: {len(updated_content)}")

        with open(output_file, 'w', encoding="utf-8") as file:
            file.write(updated_content)
    
    except Exception as e:
        print(f"Error in remove_last_letter: {str(e)}")
        # Create empty output file if processing fails
        open(output_file, 'w', encoding="utf-8").close()