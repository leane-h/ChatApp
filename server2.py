import tkinter as tk  # Importing the TKINTER library for GUI
from tkinter import filedialog, messagebox  # Importing specific modules from tkinter
from socket import *  # Importing all classes and functions from the socket module
from PIL import Image, ImageTk  # Importing classes from the Python Imaging Library for image handling
import threading  # Importing the threading module for multi-threading support
import random  # Importing the random module for generating random numbers

# Global constants and variables
mtu = 1500  # maximum Transfer Unit for UDP
ackNb = None  # initial ACK number
seqNb = None  # initial sequence number
tOut = 5  # timeout value for UDP sockets

peerIP = '127.0.0.1'  # IP address of the peer
sendPort = 12023  # Port for sending messages
receivePort = 12045  # Port for receiving messages
sendAckPort = 13023  # Port for sending ACKs
receiveAckPort = 13045  # Port for receiving ACKs

# Creating UDP sockets for sending and receiving messages and ACKs
sendSocket = socket(AF_INET, SOCK_DGRAM)  # UDP socket to send messages
receiveSocket = socket(AF_INET, SOCK_DGRAM)  # UDP socket to receive messages
sendAckSocket = socket(AF_INET, SOCK_DGRAM)  # UDP socket to send ACKs
receiveAckSocket = socket(AF_INET, SOCK_DGRAM)  # UDP socket to receive ACKs

receiveSocket.bind(('', receivePort))  # Binding receive socket to the receive port
receiveAckSocket.bind(('', receiveAckPort))  # Binding receive ACK socket to the receive ACK port

images = []  # List to store image references to prevent garbage collection

# Initializing the GUI
root = tk.Tk()  # Creating a Tkinter root window
root.title("Chat Room")  # Setting the title of the root window

# Creating a frame for chat display
chat_frame = tk.Frame(root)  # Creating a frame to hold the chat display
chat_frame.pack()  # Packing the frame into the root window

# Creating a scrollbar for the chat display
scrollbar = tk.Scrollbar(chat_frame)  # Creating a vertical scrollbar
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # Packing the scrollbar to the right side of the frame and filling the Y-axis

# Creating a text widget for chat display
chat_box = tk.Text(chat_frame, height=15, width=50, yscrollcommand=scrollbar.set, state=tk.DISABLED)  # Creating a text widget for chat display
chat_box.pack(side=tk.LEFT, fill=tk.BOTH)  # Packing the text widget to the left side of the frame and filling both X and Y axes
scrollbar.config(command=chat_box.yview)  # Configuring the scrollbar to control the y-axis of the chat box

# Creating an entry widget for typing messages
message_entry = tk.Entry(root, width=40)  # Creating an entry widget for typing messages
message_entry.pack(pady=10)  # Packing the entry widget with some vertical padding

# Function to send messages when 'Return' key is pressed or 'Send' button is clicked
def gui_send_message(event=None):
    message = message_entry.get().strip()  # Getting the message from the entry widget and removing leading/trailing whitespaces
    if message:  # Checking if the message is not empty
        message_entry.delete(0, tk.END)  # Clearing the input field
        threading.Thread(target=sendMessage, args=(message,), daemon=True).start()  # Starting a new thread to send the message

# Function to send message over UDP
def sendMessage(message):
    global mtu, seqNb, tOut  # Referencing global variables
    if seqNb is None:  # Checking if it's the first packet to generate a sequence number
        seqNb = random.randint(1, 1000)  # Generating a random sequence number
    if message == "sendf":  # Checking if the message is a trigger to send files
        send_files()  # Calling the function to send files
    else:
        packet = str(seqNb) + "<<<split>>>" + message  # Constructing the packet with sequence number and message
        try:
            sendSocket.sendto(packet.encode(), (peerIP, sendPort))  # Sending the packet over UDP
            seqNb += len(message)  # Updating the sequence number
            receiveAckSocket.settimeout(tOut)  # Setting a timeout for receiving ACKs
            response, _ = receiveAckSocket.recvfrom(mtu)  # Waiting for an ACK
            receivedAck = int(response.decode())  # Converting the received ACK to an integer
            if receivedAck == seqNb:  # Checking if the received ACK is correct
                print("Ack ", receivedAck)  # Displaying the received ACK
                root.after(0, update_chat_box, f"You: {message}")  # Updating the chat box with the sent message
                receiveAckSocket.settimeout(None)  # Resetting the timeout
            else:
                print("Not correct ACK")  # Displaying that the received ACK is incorrect
        except timeout:
            print("TIMEOUT!!")  # Displaying that a timeout occurred
        except Exception as e:
            print("ERROR!!", e)  # Handling other exceptions

# Function to update chat box with messages
def update_chat_box(message):
    chat_box.configure(state=tk.NORMAL)  # Enabling the chat box for modifications
    chat_box.insert(tk.END, f"{message}\n")  # Inserting the message into the chat box
    chat_box.configure(state=tk.DISABLED)  # Disabling the chat box to prevent user edits
    chat_box.yview(tk.END)  # Scrolling to the end of the chat box

# Function to receive messages over UDP
def receiveMessage():
    global mtu, ackNb  # Referencing global variables
    while True:  # Infinite loop to continuously receive messages
        message, _ = receiveSocket.recvfrom(mtu)  # Receiving a message from the socket
        seqNumber, receivedMessage = message.decode().split("<<<split>>>")  # Splitting the message into sequence number and actual message
        seqNumber = int(seqNumber)  # Converting the sequence number to an integer
        if ackNb is None or seqNumber == ackNb:  # Checking if it's the expected sequence number
            ackNb = seqNumber + len(receivedMessage)  # Updating the ACK number
            sendAckSocket.sendto(str(ackNb).encode(), (peerIP, sendAckPort))  # Sending an ACK
            chat_box_event = f"Received: {receivedMessage}\n"  # Constructing the event for updating the chat box
            root.after(0, update_chat_box, chat_box_event)  # Updating the chat box with the received message
        else:
            print("Unexpected sequence number. Expected:", ackNb, "Got:", seqNumber)  # handling unexpected sequence numbers

# Function to send files over TCP
def send_files():
    receiverPort = 25148  # Receiver Port listening to incoming TCP connections
    senderSocket = socket(AF_INET, SOCK_STREAM)  # Creating a TCP socket for sending files
    try:
        senderSocket.connect((peerIP, receiverPort))  # Connecting sender to receiver via TCP
        file_path = filedialog.askopenfilename(title="Select File")  # Asking user to select a file to send
        if file_path:  # Checking if a file path was selected
            file_name = file_path.split('/')[-1]  # Extracting the file name from the file path
            senderSocket.send(file_name.encode())  # Sending the file name to the receiver
            with open(file_path, 'rb') as file:  # Opening the file in binary read mode
                data = file.read()  # Reading the complete file data into memory
            senderSocket.send(data)  # Sending the binary data of the file
            senderSocket.send(b"<<<END>>>")  # Sending a specific byte sequence to indicate the end of file transfer

            # Displaying the sent file in the chatbox
            display_file_in_chatbox(file_path, 'You sent:')

    except Exception as e:  # Handling connection errors
        messagebox.showerror("Connection Error", f"Failed to connect to {peerIP}:{receiverPort}\n{e}")
    finally:
        senderSocket.close()  # Closing the sender socket after the operation completes

# Function to display received files in the chatbox
def display_file_in_chatbox(file_path, message_prefix, is_received=False):
    # Checking if the file is an image based on its extension
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        image = Image.open(file_path)  # Opening the image file
        image = image.resize((200, 150))  # Resizing the image to fit the chat box
        photo = ImageTk.PhotoImage(image)  # Converting the image to a format Tkinter can use
        images.append(photo)  # Appending the image to the list to prevent it from being garbage collected

        # Enabling the chat box for modifications
        chat_box.configure(state=tk.NORMAL)
        # Inserting a message indicating an image and adding a newline
        chat_box.insert(tk.END, f"{message_prefix} an image:\n")
        # Inserting the image at the end of the chat box content
        chat_box.image_create(tk.END, image=photo)
        # Adding a newline after the image for any following messages
        chat_box.insert(tk.END, '\n')
        # Disabling the chat box to prevent user editing
        chat_box.configure(state=tk.DISABLED)
    else:
        # Handling non-image files by extracting just the file name
        file_name = file_path.split('/')[-1] if is_received else file_path
        # Enabling the chat box for modifications
        chat_box.configure(state=tk.NORMAL)
        # Inserting the file name and a newline
        chat_box.insert(tk.END, f"{message_prefix} {file_name}\n")
        # Disabling the chat box to prevent user editing
        chat_box.configure(state=tk.DISABLED)

# Function to receive files over TCP
def receive_files():
    userPort = 45678  # Port number on which this server listens for incoming connections
    receiverSocket = socket(AF_INET, SOCK_STREAM)  # Creating a TCP socket for receiving files
    receiverSocket.bind(('', userPort))  # Binding the socket to listen
    receiverSocket.listen(1)  # Enabling the server to accept connections

    while True:  # Infinite loop to continuously accept incoming files
        connectionSocket, addr = receiverSocket.accept()  # Accepting a connection from a client
        file_name = "copy_" + connectionSocket.recv(mtu).decode()  # Receiving the initial chunk of data which contains the file name and prepending 'copy_'
        file_bytes = b""  # Initializing an empty byte string to accumulate file data
        fully_received = False  # Flag to check if file transmission is complete

        while not fully_received:  # Looping until the entire file is received
            data = connectionSocket.recv(mtu)  # Receiving data in chunks defined by 'mtu'
            if data.endswith(b"<<<END>>>"):  # Checking if the received data chunk ends with the specific end sequence '<<<END>>>'
                file_bytes += data[:-9]  # Removing the end tag from data
                fully_received = True  # Setting flag to True indicating the end of file reception
            else:
                file_bytes += data  # Adding all received data to file_bytes

        file_path = './' + file_name  # Constructing the file path where the received file will be stored
        with open(file_path, 'wb') as file:  # Opening the file in binary write mode
            file.write(file_bytes)  # Writing the accumulated bytes to the file

        # Displaying every received file in the chatbox
        display_file_in_chatbox(file_path, 'Received (on desktop)', is_received=True)
        connectionSocket.close()  # Closing the connection after the file is received

# Binding 'Return' key press event to send message
message_entry.bind("<Return>", gui_send_message)
# Creating a button to send message
send_button = tk.Button(root, text="Send", command=gui_send_message)
send_button.pack(side=tk.LEFT)  # Packing the button to the left side of the window

# Creating a button to send files
send_file_button = tk.Button(root, text="Send File", command=send_files)
send_file_button.pack(side=tk.RIGHT)  # Packing the button to the right side of the window

# Starting threads for messaging and file reception
threading.Thread(target=receiveMessage, daemon=True).start()  # Starting a thread to receive messages
threading.Thread(target=receive_files, daemon=True).start()  # Starting a thread to receive files

root.mainloop()  # Starting the Tkinter event loop


