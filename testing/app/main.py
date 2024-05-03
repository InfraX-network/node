import os

input_files = os.listdir("input")  # (1)

for file in input_files:
    with open(f"input/{file}", "r") as f:
        data = f.read()
        # Process input data

with open("output/output.txt", "w") as f:  # (2)
    f.write("Hello InfraX!")
