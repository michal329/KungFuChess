"""The networked client's Application Layer: sends commands, receives
messages, never validates game rules itself. Rendering/input
(``kfchess.gui`` / ``kfchess.input``) stay as they are; this package is
what will eventually sit between them and the server.
"""
