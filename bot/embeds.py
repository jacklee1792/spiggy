from discord import Embed

FAIL_COLOUR = 0xC10016
OK_COLOUR = 0x00B74F

NO_PERMISSION = Embed()
NO_PERMISSION.add_field(name='Uh oh!',
                        value="You don't have permission to use this command.")
