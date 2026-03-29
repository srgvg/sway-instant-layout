# sway-instant-layout

Automatic 'list based' layouts for the [sway](https://swaywm.org) window manager.

## Attribution

This project is a fork of [i3-instant-layout](https://github.com/TyberiusPrime/i3-instant-layout) by TyberiusPrime (Florian Finkernagel), forked at commit [`0d6a983`](https://github.com/TyberiusPrime/i3-instant-layout/commit/0d6a983dd06dce8f666982870ef765e1bbade6bb).

The original tool targets i3 (X11). This fork ports it to sway (Wayland) by replacing the `xdotool` unmap/remap + i3 window-swallow mechanism with direct sway IPC window repositioning via the scratchpad.

## Status

Beta. The core layout logic is unchanged from the original. The sway-specific window placement mechanism (scratchpad + split/focus IPC commands) is new and may have edge cases. Testing and bug reports welcome.

## Animated summary

![Demo of i3-instant-layout](https://github.com/TyberiusPrime/i3-instant-layout/raw/master/docs/_static/i3-instant-layout_demo.gif "i3-instant-layout demo (from original i3 version)")

## Description

This python program drags sway into the 'managed layouts tiling window manager world' kicking and screaming.

What it does is apply a window layout to your current workspace,
like this one:

    -------------
    |     |  2  |
    |     |-----|
    |  1  |  3  |
    |     |-----|
    |     |  4  |
    -------------

The big advantage here is that it needs no pre-configuration whatsoever —
it's 'instant'. Just press the button.

## Get started

Install with `pip install sway-instant-layout`, or if you prefer, [pipx](https://github.com/pipxproject/pipx).

Add this to your sway config:
```
bindsym $mod+Escape exec "sway-instant-layout --list | wofi --dmenu | sway-instant-layout -"
```
(or use `rofi --dmenu -i` or any other dmenu-compatible launcher of your choice — rofi works on Wayland too).

No external tools beyond sway's IPC are required.

## Further information

Call `sway-instant-layout --help` for full details, or
`sway-instant-layout --desc` for the full list of supported layouts (or see below).

## Helpful tips

### How to sort windows
Your current active window is what the tiler will consider the 'main window'.

To get the other windows in the right order for your layout of choice,
first enable the vStack or hStack layout, sort them,
and then proceed to your layout of choice.

### How it works (sway port)

Unlike the original i3 version, this port does **not** use `xdotool` or i3's window
swallowing mechanism (which are X11-only). Instead it uses sway's IPC directly:

1. All tiled windows in the workspace are moved to the scratchpad.
2. Windows are placed back one by one using `split h/v`, `focus parent`, and
   `layout tabbed` commands to build the target container tree.
3. Focus is restored to the original active window.


## Available layouts

Layout: vStack

Aliases: ['1col', '1c']

One column / a vertical stack.

	---------
	|   1   |
	---------
	|   2   |
	---------
	|   3   |
	---------


--------------------------------------------------------------------------------

Layout: hStack

Aliases: ['1row', '1r']

One row / a horizontal stack

	-------------
	|   |   |   |
	| 1 | 2 | 3 |
	|   |   |   |
	-------------


--------------------------------------------------------------------------------

Layout: v2Stack

Aliases: ['2col', '2c', '2v']

Two columns of stacks

	-------------
	|  1  |  4  |
	-------------
	|  2  |  5  |
	-------------
	|  3  |  6  |
	-------------


--------------------------------------------------------------------------------

Layout: h2Stack

Aliases: ['2row', '2r', '2h']

Two rows of stacks

	-------------------
	|  1  |  2  |  3  |
	-------------------
	|  4  |  5  |  6  |
	-------------------


--------------------------------------------------------------------------------

Layout: v3Stack

Aliases: ['3col', '3c', '3v']

Three columns of stacks

	-------------------
	|  1  |  3  |  5  |
	-------------------
	|  2  |  4  |  6  |
	-------------------


--------------------------------------------------------------------------------

Layout: h3Stack

Aliases: ['3row', '3r', '3h']

Three rows of stacks

	-------------------
	|  1  |  2  |  3  |
	-------------------
	|  4  |  5  |  6  |
	-------------------
	|  7  |  8  |  9  |
	-------------------


--------------------------------------------------------------------------------

Layout: max

Aliases: ['maxTabbed']

One large container, in tabbed mode.

	---------------
	|             |
	|   1,2,3,4,  |
	|             |
	---------------


--------------------------------------------------------------------------------

Layout: mainLeft

Aliases: ['ml', 'mv', 'MonadTall']

One large window to the left at 50%,
all others stacked to the right vertically.

	-------------
	|     |  2  |
	|     |-----|
	|  1  |  3  |
	|     |-----|
	|     |  4  |
	-------------


--------------------------------------------------------------------------------

Layout: mainRight

Aliases: ['mr', 'vm', 'MonadTallFlip']

One large window to the right at 50%,
all others stacked to the right vertically.

	-------------
	|  2  |     |
	|-----|     |
	|  3  |  1  |
	|-----|     |
	|  4  |     |
	-------------


--------------------------------------------------------------------------------

Layout: MainMainVStack

Aliases: ['mmv']

Two large windows to the left at 30%,
all others stacked to the right vertically.

	-------------------
	|     |     |  3  |
	|     |     |-----|
	|  1  |  2  |  4  |
	|     |     |-----|
	|     |     |  5  |
	-------------------


--------------------------------------------------------------------------------

Layout: MainVStackMain

Aliases: ['mvm']

Two large windows at 30% to the left and right,
a vstack in the center

	-------------------
	|     |  3  |     |
	|     |-----|     |
	|  1  |  4  |  2  |
	|     |-----|     |
	|     |  5  |     |
	-------------------


--------------------------------------------------------------------------------

Layout: matrix

Aliases: []

Place windows in a n * n matrix.

N is math.ceil(math.sqrt(window_count))


--------------------------------------------------------------------------------

Layout: VerticalTileTop

Aliases: ['vtt']

Large master area (66%) on top,
horizontal stacking below


--------------------------------------------------------------------------------

Layout: VerticalTileBottom

Aliases: ['vtb']

Large master area (66%) on bottom,
horizontal stacking above


--------------------------------------------------------------------------------

Layout: NestedRight

Aliases: ['nr']

Nested layout, starting with a full left half.


	-------------------------
	|           |           |
	|           |     2     |
	|           |           |
	|     1     |-----------|
	|           |     |  4  |
	|           |  3  |-----|
	|           |     |5 | 6|
	-------------------------


--------------------------------------------------------------------------------

Layout: SmartNestedRight

Aliases: ['snr']

Nested layout, starting with a full left half,
but never going below 1/16th of the size.

	2 windows
	-------------------------
	|           |           |
	|           |           |
	|           |           |
	|     1     |     2     |
	|           |           |
	|           |           |
	|           |           |
	-------------------------

	5 windows
	-------------------------
	|           |           |
	|           |     2     |
	|           |           |
	|     1     |-----------|
	|           |     |  4  |
	|           |  3  |-----|
	|           |     |  5  |
	-------------------------

Falls back to matrix layout above 16 windows.

--------------------------------------------------------------------------------

Layout: mainCenter

Aliases: ['mc', 'vmv']
One large window in the middle at 50%,
all others stacked to the left/right vertically.

	-------------------
	|  2  |     |  5  |
	|-----|     |-----|
	|  3  |  1  |  6  |
	|-----|     |-----|
	|  4  |     |  7  |
	-------------------

--------------------------------------------------------------------------------

Layout: mainTop

Aliases: ['mt']

One large window to the top at 50%,
all others stacked horizontally below.

	-------------
	|           |
	|     1     |
	|           |
	|-----|-----|
	|  2  |  3  |
	-------------

--------------------------------------------------------------------------------
