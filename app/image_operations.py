from PIL import Image
import random
import os
import struct

def ascii_to_rgb(rgb_file, image_name):
    colors = []
    
    # First, read the actual data
    with open(rgb_file, "r") as f:
        for line in f:
            try:
                value = int(line.strip())
                colors.append(value)
            except ValueError:
                continue  # Skip invalid values
    
    original_length = len(colors)
    print(f"Read {original_length} color values")
    
    # Store the length in the first pixel
    length_bytes = struct.pack('>I', original_length)
    header = list(length_bytes)  # Convert to list of 4 bytes
    
    # Combine header and data
    all_values = header + colors
    
    # Now, calculate image dimensions based on all_values
    total_values = len(all_values)
    
    # Make sure we have a multiple of 3 for RGB pixels
    if total_values % 3 != 0:
        padding_needed = 3 - (total_values % 3)
        all_values.extend([0] * padding_needed)
        total_values += padding_needed
    
    total_pixels = total_values // 3
    
    # Calculate dimensions - use square-ish dimensions
    width = int(total_pixels ** 0.5)
    height = (total_pixels + width - 1) // width  # Ceiling division
    
    # Ensure we have enough values for width*height pixels
    pixels_needed = width * height * 3
    if len(all_values) < pixels_needed:
        padding = [0] * (pixels_needed - len(all_values))
        all_values.extend(padding)
    
    print(f"Creating image with dimensions {width}x{height} (total pixels: {width*height})")
    
    # Convert to bytes for image creation
    img_data = bytes(all_values)
    img = Image.frombytes('RGB', (width, height), img_data)
    img.save(image_name)
    
    return image_name

def de_png_to_rgb(image_path, output_file):
    try:
        # Open the image and get raw pixel data
        image = Image.open(image_path)
        width, height = image.size
        raw_data = image.tobytes()
        
        print(f"Decrypting image with dimensions {width}x{height}, data length: {len(raw_data)}")
        
        # First 4 bytes are the length
        original_length = struct.unpack('>I', raw_data[:4])[0]
        print(f"Original data length: {original_length}")
        
        # The rest is the actual color data
        data_bytes = raw_data[4:]
        
        # Write to output file
        with open(output_file, 'w') as f:
            # Only write up to original_length values
            count = 0
            for i in range(len(data_bytes)):
                if count >= original_length:
                    break
                f.write(f"{data_bytes[i]}\n")
                count += 1
        
        print(f"Wrote {count} values to output file")
    
    except Exception as e:
        print(f"Error in de_png_to_rgb: {str(e)}")
        # Create empty file if decryption fails
        open(output_file, 'w').close()

# Encryption process
def encrypt_file(filepath):
    # Ensure temp and enimg directories exist
    os.makedirs('temp', exist_ok=True)
    os.makedirs('enimg', exist_ok=True)
    
    from file_operations import text_to_binary, binary_to_ascii
    
    print(f"Converting text file to binary: {filepath}")
    text_to_binary(filepath, 'temp/bin_en.txt')
    print(f"Converting binary to ASCII: temp/bin_en.txt")
    binary_to_ascii("temp/bin_en.txt", "temp/output_ascii_en.txt")
    
    # Generate unique filename
    i = 1
    img_name = f"enimg/Demo{i}.png"

    while os.path.exists(img_name):  # Check if file exists
        i += 1
        img_name = f"enimg/Demo{i}.png"

    # Convert ASCII to image
    print(f"Converting ASCII to image: temp/output_ascii_en.txt -> {img_name}")
    return ascii_to_rgb("temp/output_ascii_en.txt", img_name)

# Decryption process
def decrypt_file(filepath):
    # Ensure temp directory exists
    os.makedirs('temp', exist_ok=True)
    
    from file_operations import rgb_binary_de, join_lines_with_space, de_bin_to_text, remove_last_letter
    
    print(f"Converting image to RGB values: {filepath}")
    de_png_to_rgb(filepath, "temp/output_acsii_de.txt")
    
    print("Converting RGB values to binary")
    rgb_binary_de("temp/output_acsii_de.txt", "temp/bin_de.txt")
    
    print("Joining binary values with spaces")
    join_lines_with_space('temp/bin_de.txt', 'temp/sbin_de.txt')
    
    print("Converting binary to text")
    de_bin_to_text('temp/sbin_de.txt', 'temp/lbin_de.txt')
    
    output_txt_file = 'temp/output.txt'
    print(f"Removing last letter and saving to {output_txt_file}")
    remove_last_letter('temp/lbin_de.txt', output_txt_file)
    
    return output_txt_file