# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""


import hashlib
import os
from pathlib import Path

from qgis.PyQt import QtCore, QtGui

from .definitions.defaults import DOCUMENTATION_SITE, REPORT_FONT_NAME, TEMPLATE_NAME
from cplus_core.definitions.constants import (
    NCS_CARBON_SEGMENT,
    NCS_PATHWAY_SEGMENT,
    PRIORITY_LAYERS_SEGMENT,
)
from cplus_core.utils.helper import *  # noqa


def write_to_file(message, file_path):
    with open(file_path, "w+") as f:
        f.write(message)


def open_documentation(url=None):
    """Opens documentation website in the default browser

    :param url: URL link to documentation site (e.g. gh pages site)
    :type url: str

    """
    url = DOCUMENTATION_SITE if url is None else url
    result = QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
    return result


def get_plugin_version() -> [str, None]:
    """Returns the current plugin version
    as saved in the metadata.txt plugin file.

    :returns version: Plugin version
    :rtype version: str
    """
    metadata_file = Path(__file__).parent.resolve() / "metadata.txt"

    with open(metadata_file, "r") as f:
        for line in f.readlines():
            if line.startswith("version"):
                version = line.strip().split("=")[1]
                return version
    return None


def get_report_font(size=11.0, bold=False, italic=False) -> QtGui.QFont:
    """Uses the default font family name to create a
    font for use in the report.

    :param size: The font point size, default is 11.
    :type size: float

    :param bold: True for bold font else False which is the default.
    :type bold: bool

    :param italic: True for font to be in italics else False which is the default.
    :type italic: bool

    :returns: Font to use in a report.
    :rtype: QtGui.QFont
    """
    font_weight = 50
    if bold is True:
        font_weight = 75

    return QtGui.QFont(REPORT_FONT_NAME, int(size), font_weight, italic)


def contains_font_family(font_family: str) -> bool:
    """Checks if the specified font family exists in the font database.

    :param font_family: Name of the font family to check.
    :type font_family: str

    :returns: True if the font family exists, else False.
    :rtype: bool
    """
    font_families = QtGui.QFontDatabase().families()
    matching_fonts = [family for family in font_families if font_family in family]

    return True if len(matching_fonts) > 0 else False


def install_font(dir_name: str) -> bool:
    """Installs the font families in the specified folder name under
    the plugin's 'fonts' folder.

    :param dir_name: Directory name, under the 'fonts' folder, which
    contains the font families to be installed.
    :type dir_name: str

    :returns: True if the font(s) were successfully installed, else
    False if the directory name does not exist or if the given font
    families already exist in the application's font database.
    :rtype: bool
    """
    font_family_dir = os.path.normpath(f"{FileUtils.get_fonts_dir()}/{dir_name}")
    if not os.path.exists(font_family_dir):
        tr_msg = tr("font directory does not exist.")
        log(message=f"'{dir_name}' {tr_msg}", info=False)

        return False

    status = True
    font_paths = Path(font_family_dir).glob("**/*")
    font_extensions = [".otf", ".ttf"]
    for font_path in font_paths:
        if font_path.suffix not in font_extensions:
            continue
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path.as_posix())
        if font_id == -1 and status:
            tr_msg = "font could not be installed."
            log(message=f"'{font_path}' {tr_msg}", info=False)
            status = False

    return status


class FileUtils(BaseFileUtils):
    """
    Provides functionality for commonly used file-related operations.
    """

    @staticmethod
    def plugin_dir() -> str:
        """Returns the root directory of the plugin.

        :returns: Root directory of the plugin.
        :rtype: str
        """
        return os.path.join(os.path.dirname(os.path.realpath(__file__)))

    @staticmethod
    def get_fonts_dir() -> str:
        """Returns the fonts directory in the plugin.

        :returns: Fonts directory.
        :rtype: str
        """
        return f"{FileUtils.plugin_dir()}/data/fonts"

    @staticmethod
    def get_icon(file_name: str) -> QtGui.QIcon:
        """Creates an icon based on the icon name in the 'icons' folder.

        :param file_name: File name which should include the extension.
        :type file_name: str

        :returns: Icon object matching the file name.
        :rtype: QtGui.QIcon
        """
        icon_path = os.path.normpath(f"{FileUtils.plugin_dir()}/icons/{file_name}")

        if not os.path.exists(icon_path):
            return QtGui.QIcon()

        return QtGui.QIcon(icon_path)

    @staticmethod
    def report_template_path(file_name=None) -> str:
        """Get the absolute path to the template file with the given name.
        Caller needs to verify that the file actually exists.

        :param file_name: Template file name including the extension. If
        none is specified then it will use `main.qpt` as the default
        template name.
        :type file_name: str

        :returns: The absolute path to the template file with the given name.
        :rtype: str
        """
        if file_name is None:
            file_name = TEMPLATE_NAME

        absolute_path = f"{FileUtils.plugin_dir()}/data/reports/{file_name}"

        return os.path.normpath(absolute_path)

    @staticmethod
    def create_ncs_pathways_dir(base_dir: str):
        """Creates an NCS subdirectory under BASE_DIR. Skips
        creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        ncs_pathway_dir = f"{base_dir}/{NCS_PATHWAY_SEGMENT}"
        message = tr(
            "Missing parent directory when creating NCS pathways subdirectory."
        )
        FileUtils.create_new_dir(ncs_pathway_dir, message)

    @staticmethod
    def create_ncs_carbon_dir(base_dir: str):
        """Creates an NCS subdirectory for carbon layers under BASE_DIR.
        Skips creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        ncs_carbon_dir = f"{base_dir}/{NCS_CARBON_SEGMENT}"
        message = tr("Missing parent directory when creating NCS carbon subdirectory.")
        FileUtils.create_new_dir(ncs_carbon_dir, message)

    def create_pwls_dir(base_dir: str):
        """Creates priority weighting layers subdirectory under BASE_DIR.
        Skips creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        pwl_dir = f"{base_dir}/{PRIORITY_LAYERS_SEGMENT}"
        message = tr(
            "Missing parent directory when creating priority weighting layers subdirectory."
        )
        FileUtils.create_new_dir(pwl_dir, message)


def md5(fname):
    """
    Get md5 checksum off a file
    """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
