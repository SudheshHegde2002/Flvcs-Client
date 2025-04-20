from flvcs.data_utils import get_auth_file, load_user_auth, delete_user_auth

# Show the auth file location
auth_file = get_auth_file()
print(f"Auth file location: {auth_file}")

# Show current auth status
auth_data = load_user_auth()
if auth_data:
    print(f"Currently authenticated with UID: {auth_data.get('uid', 'Unknown')}")
else:
    print("Not currently authenticated")

# Option to delete credentials
if auth_data:
    choice = input("Would you like to delete credentials? (y/n): ")
    if choice.lower() == 'y':
        delete_user_auth()
        print("Credentials deleted")
        
        # Verify deletion
        if load_user_auth():
            print("WARNING: Credentials still exist")
        else:
            print("Verification: Credentials successfully deleted") 