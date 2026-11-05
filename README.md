# Peer-to-Peer Chat App (Reliable UDP + TCP File Transfer)


A two-peer desktop chat application with a Tkinter GUI. Text messages are sent over **UDP** with a
sequence/acknowledgement scheme added on top for reliability, and files of any type (images,
documents, binaries, …) are sent over a **separate TCP connection**. Both peers act as servers:
each one is always listening for incoming messages and files while the user is typing.

---

## Project files

| File | Description |
|------|-------------|
| `server1.py` | Peer 1. Same code as peer 2, with mirrored port numbers. |
| `server2.py` | Peer 2. Same code as peer 1, with mirrored port numbers. |
| `requirements.txt` | Python packages to install (Pillow). |

---

## How the app works

### 1. Chat messages: reliable UDP

UDP does not guarantee delivery, ordering, or duplicate removal, so the app adds these on top:

**Packet format**

```
<sequence number><<<split>>><message text>
```

**Sender (`sendMessage`)**
1. On the first message, the sender picks a random initial sequence number (1–1000).
2. It sends the packet over UDP to the peer.
3. It advances its sequence number by the length of the message (byte-stream numbering, like TCP).
4. It waits up to `tOut` = 5 seconds for an ACK on a dedicated ACK socket.
5. If the ACK equals the expected next sequence number, the message counts as delivered and shows
   in the chat as `You: <message>`. This is the delivery report. A wrong ACK or a timeout is logged
   to the console and the message is not shown as delivered.

**Receiver (`receiveMessage`)**
1. Runs in a background thread and listens continuously.
2. Splits the packet into sequence number and payload.
3. Accepts the packet only if its sequence number is the one expected (`ackNb`). The first packet
   received sets the starting point.
4. Sends back an ACK equal to `sequence number + message length` (the next byte it expects).
5. Shows the message as `Received: <message>`.
6. Drops duplicate or out-of-order packets (their sequence number doesn't match) and logs
   `Unexpected sequence number. Expected: X Got: Y`.

This ensures messages are shown **in order** and **without duplicates**. Messages and ACKs use
separate sockets/ports so a peer can send and receive at the same time.

**Maximum message size:** packets are read in buffers of `mtu = 1500` bytes, so a chat message
(header included) must fit in 1500 bytes.

### 2. File transfer: TCP

Click **Send File** (or type `sendf` in the message box and press Enter):

1. The sender opens a TCP connection to the peer's file-receiving port.
2. A file picker opens. The sender sends the file name, then the file's raw bytes, then an
   end-of-file marker `<<<END>>>`.
3. The receiver (`receive_files`, background thread) reads data until it sees the marker, then
   saves the file as `copy_<original name>` in the **folder the receiver was started from**.
4. Both sides show the transfer in the chat. Images (`.png .jpg .jpeg .gif .bmp`) are shown as a
   thumbnail; other files show by name.

TCP already handles retransmission, ordering, and error checking, so file transfers stay correct
when the network is unreliable.

### 3. Port layout

Both peers run on `127.0.0.1` by default. The two scripts use mirrored ports so that each peer's
"send" port is the other's "receive" port:

| Purpose | `server1.py` | `server2.py` |
|---------|--------------|--------------|
| Receives chat messages on (UDP) | 12023 | 12045 |
| Sends chat messages to (UDP) | 12045 | 12023 |
| Receives ACKs on (UDP) | 13023 | 13045 |
| Sends ACKs to (UDP) | 13045 | 13023 |
| Receives files on (TCP) | 25148 | 45678 |
| Sends files to (TCP) | 45678 | 25148 |

---

## Requirements

- **Python 3.8+**
- **Tkinter** (GUI). Included with Python on Windows/macOS. On Ubuntu/Debian:
  ```bash
  sudo apt install python3-tk
  ```
- **Pillow** (image previews in the chat):
  ```bash
  pip install -r requirements.txt
  ```
- **netem** (optional, Linux only, for testing over an unreliable network). Part of the `iproute2`
  package, which Ubuntu installs by default.

---

## Running the app

1. Install the requirements (see above).
2. Open **two terminals** in the project folder.
3. Terminal 1:
   ```bash
   python3 server1.py
   ```
4. Terminal 2:
   ```bash
   python3 server2.py
   ```
   (On Windows, use `python` instead of `python3`.)
5. A **Chat Room** window opens for each peer. Type a message and press **Enter** or click
   **Send**. It appears as `Received: ...` in the other window.
6. To send a file, click **Send File**, pick any file, and it shows up in the other peer's
   folder as `copy_<filename>`.

Debug output (ACK numbers, timeouts, unexpected sequence numbers) is printed to the terminal that
started each peer.

### Running on two different machines

Set `peerIP` near the top of each script to the **other** machine's IP address, for example:

```python
peerIP = '192.168.1.20'   # in server1.py, the IP of the machine running server2.py
```

Make sure the firewall on both machines allows the UDP and TCP ports listed above.

---

## Testing over an unreliable network (netem)

On Linux, netem can add loss, corruption, duplication, delay, and bandwidth limits to an interface.
When both peers run on the same machine, apply the rules to the loopback interface `lo`:

```bash
# Add 10% loss, 5% duplicates, 2% corruption, 100ms ± 20ms delay
sudo tc qdisc add dev lo root netem loss 10% duplicate 5% corrupt 2% delay 100ms 20ms

# Change the rules while it's running
sudo tc qdisc change dev lo root netem loss 25% delay 300ms

# Limit bandwidth
sudo tc qdisc change dev lo root netem rate 1mbit delay 50ms

# Show current rules
tc qdisc show dev lo

# Remove all rules (restore normal network)
sudo tc qdisc del dev lo root
```

When testing on two machines, replace `lo` with the network interface (e.g. `eth0`, `wlan0`;
see `ip a`). While the rules are active, send chat messages and files and check the terminal
output for timeouts and rejected (duplicate/out-of-order) packets.

> **Remember** to run `sudo tc qdisc del dev lo root` when you're done, or the rules will keep
> slowing down your machine's loopback traffic.
