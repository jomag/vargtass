# Vargtass 3D

## Doors

Doors are not that tricky to implement. If a ray intersects with a door tile, extend the
ray another half step and check if it's still within the tile. If so, the door has been
hit.

The problem I got stuck on was how to do the same for the starting tile, where the ray
does not enter from one of the sides, but rather starts at the fractional position of
the tile the player is positioned at. This can be done, but the math is a bit more
tricky and requires special handling that does not exist in the original Wolf3D code.

After banging my head on this for a while, I found two things in the original code:

First, players are not allowed to enter door tiles unless they are fully open, and
likewise doors may not be closed until the player has left the tile. This does away
with handling the special case of a player being within the door tile.

Second, Wolf3D does some preprocessing of the tiles where it among other things builds
a map where tiles adjacent to doors are marked. This makes it easier to know when to
draw the sides of a door, rather than the default texture of the tile.

## References

[Game Engine Black Book: Wolfenstein 3D](https://fabiensanglard.net/gebbwolf3d/index.html) by Fabien Sanglard.

[Wolfenstein 3D game file specifications](https://vpoupet.github.io/wolfenstein/docs/files.html)

[ModdingWiki](https://moddingwiki.shikadi.net/wiki/GameMaps_Format)


