# Copyright 2020-2020 the openage authors. See copying.md for legal info.
#
# pylint: disable=too-many-lines,too-many-branches,too-many-statements
#
# TODO:
# pylint: disable=line-too-long
"""
Convert data from DE2 to openage formats.
"""

import openage.convert.value_object.conversion.aoc.internal_nyan_names as aoc_internal
import openage.convert.value_object.conversion.de2.internal_nyan_names as de2_internal

from .....log import info
from ....entity_object.conversion.aoc.genie_graphic import GenieGraphic
from ....entity_object.conversion.aoc.genie_object_container import GenieObjectContainer
from ....entity_object.conversion.aoc.genie_unit import GenieUnitObject
from ....service.debug_info import debug_converter_objects,\
    debug_converter_object_groups
from ....service.read.nyan_api_loader import load_api
from ..aoc.pregen_processor import AoCPregenSubprocessor
from ..generic.processor import GenericProcessor
from .media_subprocessor import DE2MediaSubprocessor
from .modpack_subprocessor import DE2ModpackSubprocessor
from .nyan_subprocessor import DE2NyanSubprocessor


class DE2Processor(GenericProcessor):
    """
    Main processor for converting data from DE2.
    """
    def __init__(self, pregen_sub, nyan_sub, media_sub, modpack_sub, ambients, variants):
        super().__init__(
            AoCPregenSubprocessor(),
            DE2NyanSubprocessor(),
            DE2MediaSubprocessor(),
            DE2MediaSubprocessor(),
            {**aoc_internal.AMBIENT_GROUP_LOOKUPS, **de2_internal.AMBIENT_GROUP_LOOKUPS},
            {**aoc_internal.VARIANT_GROUP_LOOKUPS, **de2_internal.VARIANT_GROUP_LOOKUPS}
        )

    def extract_genie_units(self, gamespec, full_data_set):
        """
        Extract units from the game data.

        :param gamespec: Gamedata from empires.dat file.
        :type gamespec: class: ...dataformat.value_members.ArrayMember
        """
        # Units are stored in the civ container.
        # All civs point to the same units (?) except for Gaia which has more.
        # Gaia also seems to have the most units, so we only read from Gaia
        #
        # call hierarchy: wrapper[0]->civs[0]->units
        raw_units = gamespec[0]["civs"][0]["units"].get_value()

        # Unit headers store the things units can do
        raw_unit_headers = gamespec[0]["unit_headers"].get_value()

        for raw_unit in raw_units:
            unit_id = raw_unit["id0"].get_value()
            unit_members = raw_unit.get_value()

            # Turn attack and armor into containers to make diffing work
            if "attacks" in unit_members.keys():
                attacks_member = unit_members.pop("attacks")
                attacks_member = attacks_member.get_container("type_id")
                armors_member = unit_members.pop("armors")
                armors_member = armors_member.get_container("type_id")

                unit_members.update({"attacks": attacks_member})
                unit_members.update({"armors": armors_member})

            unit = GenieUnitObject(unit_id, full_data_set, members=unit_members)
            full_data_set.genie_units.update({unit.get_id(): unit})

            # Commands
            if "unit_commands" not in unit_members.keys():
                unit_commands = raw_unit_headers[unit_id]["unit_commands"]
                unit.add_member(unit_commands)

    def extract_genie_graphics(self, gamespec, full_data_set):
        """
        Extract graphic definitions from the game data.

        :param gamespec: Gamedata from empires.dat file.
        :type gamespec: class: ...dataformat.value_members.ArrayMember
        """
        # call hierarchy: wrapper[0]->graphics
        raw_graphics = gamespec[0]["graphics"].get_value()

        for raw_graphic in raw_graphics:
            # Can be ignored if there is no filename associated
            filename = raw_graphic["filename"].get_value().lower()
            if not filename:
                continue

            graphic_id = raw_graphic["graphic_id"].get_value()
            graphic_members = raw_graphic.get_value()
            graphic = GenieGraphic(graphic_id, full_data_set, members=graphic_members)

            if filename not in full_data_set.existing_graphics:
                graphic.exists = False

            full_data_set.genie_graphics.update({graphic.get_id(): graphic})

        # Detect subgraphics
        for genie_graphic in full_data_set.genie_graphics.values():
            genie_graphic.detect_subgraphics()
