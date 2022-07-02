New pygase-based system
# Events
## Handshake (In order)
### JOIN C->S
* name: *str*
* secret: *str*
### PLAYER_CREATED S->1C
* accepted: *bool*
* msg: *str*
### *Done, go to play mode*

-----------------------
## Play (continuous)
### UPDATE_INPUT C->S
* angle: *float*
* sprinting: *bool*

# Gamestate
## Snake[]
* uuid: *str*
* name: *str* (Not unique)
* alive: *bool*
* head: *Segment*
* segments: *Segment[]*
### Segment
* radius: *float*
* angle: *float-degrees*
* pos: *tuple*: (x: *int*, y: *int*)
* col: *tuple*: (r: *int*, g: *int*, b: *int*)
* uuid: *str*

## Food[]
* uuid: *str*
* pos: *tuple*: (x: *int*, y: *int*)
* col: *tuple*: (r: *int*, g: *int*, b: *int*)
* radius: *float*
* mass_multiplier: *float*

## GameInfo
* border: *int*
* max_turn: *float*