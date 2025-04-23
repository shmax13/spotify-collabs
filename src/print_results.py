import csv

def print_predictions_from_csv(log_path="data/predicted_collaborations.csv"):
    try:
        # Open the CSV file for reading
        with open(log_path, 'r', encoding='utf-8') as log_file:
            reader = csv.DictReader(log_file)  # Read the file as a dictionary
            print("Predicted Collaborations (Logical Knowledge):")
            
            # Loop through each row in the CSV
            for row in reader:
                # Print formatted results
                print(f"{row['Artist 1']} x {row['Artist 2']} — Shared Neighbors: {row['Shared Neighbors']}, Genre Overlap: {row['Genre Overlap']}, Popularity Diff: {row['Popularity Diff']}")
    except FileNotFoundError:
        print(f"Error: The file at {log_path} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    print_predictions_from_csv()