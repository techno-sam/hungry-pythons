#Protocol

###Notes
* Angles are radians (float)

##Handshake
1. **C2S Init** `{str name, str secret}`
2. **S2C Respond** `{bool accepted, (opt)str reason}`
3. *(If accepted)* **C2S Request Game Info**
4. **S2C Game Info** `{num borderdistance, num max_turn}`
5. **C2S Start Game** `{}`

##Client-To-Server (C2S)
* **Update Input** `{num angle, bool sprinting}`
* **Quit** `{}`
* **Resend** `{}`
  * Requests server to resend all game items (segments and food)

##Snake Class
class Snake:
    def __init__(self, uuid):
        self.head = None
        self.segments = []
        self.name = "Player"
        self.secret = ""
        self.alive = True
        self.mousedown = False
        self.mouseangle = 0
        self.uuid = uuid
        self.last_update = time.time()
        self.last_message = time.time()

##Server-To-Client (S2C)
* **Modify Snake** `{str uuid, bool isown, str name, bool alive, bool mousedown, Segment head, Segment[] segments}`
  * **Segment** `{bool ishead, num radius, num angle, tup pos(num x, num y), tup col(num r, num g, num b), num idx}`
    * Adds if segment does not exist yet
    * `idx` is index in snake (head 0, first segment 1, etc...)
* **Remove Snake** `{str uuid}`
* **Add Food** `{str uuid, tup pos(num x, num y), tup col(num r, num g, num b), num radius, num energy}`
* **Remove Food** `{str uuid}`
* **Kill** `{(opt)str msg}`
  * Message can be:
    * You ran into the border.
    * You stubbed your nose on [killer].
    * You didn't see [killer] ahead of you.
    * You bumped into [killer].
    * You thought [killer] was a ghost.
* **Resending** `{}`
  * Confirmation from server that it is resending, client clears items