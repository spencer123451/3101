# Read the text file
x="data/newoutput.txt"
with open(x, 'r') as file:
    lines = file.readlines()

# Calculate the number of lines for the top 10%
top_10_percent_count = int(len(lines) * 0.05)

# Get the top 10% of lines
top_10_percent_lines = lines[:top_10_percent_count]

# Optionally, write the top 10% to a new file
with open('top_10_percent.txt', 'w') as file:
    file.writelines(top_10_percent_lines)

for line in top_10_percent_lines:
    print(line.strip())

    
