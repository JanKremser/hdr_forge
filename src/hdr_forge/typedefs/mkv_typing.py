from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Type, TypeVar, Tuple


# Define T as a TypeVar that must be a dataclass
T = TypeVar('T')

def split_known_unknown_fields(data_dict: Dict[str, Any], dataclass_type: Type[T]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Split dictionary into known fields (that match dataclass fields) and unknown fields.

    Args:
        data_dict: Dictionary with data
        dataclass_type: Dataclass type to check against

    Returns:
        Tuple of (known_fields_dict, unknown_fields_dict)
    """
    if not is_dataclass(dataclass_type):
        raise TypeError(f"Expected dataclass type, got {dataclass_type}")

    known_fields = {}
    unknown_fields = {}

    # Get field names from the dataclass
    dataclass_field_names = {f.name for f in fields(dataclass_type)}

    for key, value in data_dict.items():
        if key in dataclass_field_names:
            known_fields[key] = value
        else:
            unknown_fields[key] = value

    return known_fields, unknown_fields


def add_dynamic_attributes(instance: Any, attributes: Dict[str, Any]) -> None:
    """
    Add dynamic attributes to an object instance.

    Args:
        instance: Object to add attributes to
        attributes: Dictionary of attribute name/value pairs
    """
    for key, value in attributes.items():
        setattr(instance, key, value)


@dataclass
class MkvChapter:
    """Chapter information of an MKV file."""
    num_entries: int


@dataclass
class MkvContainerProperties:
    """Properties of the MKV container."""
    # Make all fields optional with default values
    container_type: Optional[int] = None
    date_local: Optional[str] = None
    date_utc: Optional[str] = None
    duration: Optional[int] = None
    is_providing_timestamps: Optional[bool] = None
    muxing_application: Optional[str] = None
    segment_uid: Optional[str] = None
    timestamp_scale: Optional[int] = None
    title: Optional[str] = None
    writing_application: Optional[str] = None

    # Additional dynamic properties handling
    def __post_init__(self):
        # Store any additional properties that weren't explicitly defined
        for key, value in self.__dict__.copy().items():
            if key.startswith("_unknown_"):
                real_key = key[len("_unknown_"):]
                setattr(self, real_key, value)
                delattr(self, key)


@dataclass
class MkvContainer:
    """Container information of an MKV file."""
    properties: MkvContainerProperties
    recognized: bool
    supported: bool
    type: str


@dataclass
class MkvTrackProperties:
    """Properties of an MKV track."""
    # Make all previously required fields optional with default values
    uid: Optional[int] = None
    language: Optional[str] = None
    default_track: Optional[bool] = None
    enabled_track: Optional[bool] = None
    forced_track: Optional[bool] = None

    codec_id: Optional[str] = None
    codec_private_length: Optional[int] = None
    minimum_timestamp: Optional[int] = None
    number: Optional[int] = None
    codec_private_data: Optional[str] = None
    default_duration: Optional[int] = None
    display_dimensions: Optional[str] = None
    display_unit: Optional[int] = None
    num_index_entries: Optional[int] = None
    packetizer: Optional[str] = None
    pixel_dimensions: Optional[str] = None
    audio_channels: Optional[int] = None
    audio_sampling_frequency: Optional[int] = None
    audio_bits_per_sample: Optional[int] = None
    track_name: Optional[str] = None

    # MPEG Transport Stream specific fields
    program_number: Optional[int] = None
    stream_id: Optional[int] = None

    # Tag information
    tag__statistics_tags: Optional[str] = None
    tag__statistics_writing_app: Optional[str] = None
    tag__statistics_writing_date_utc: Optional[str] = None
    tag_bps: Optional[str] = None
    tag_duration: Optional[str] = None
    tag_number_of_bytes: Optional[str] = None
    tag_number_of_frames: Optional[str] = None
    tag_source_id: Optional[str] = None

    # Additional dynamic properties
    def __post_init__(self):
        # Convert all unknown properties to attributes
        for key, value in self.__dict__.copy().items():
            if key.startswith("_unknown_"):
                real_key = key[len("_unknown_"):]
                setattr(self, real_key, value)
                delattr(self, key)


class MkvTrackType(Enum):
    VIDEO = 'video'
    AUDIO = 'audio'
    SUBTITLES = 'subtitles'
    UNKNOWN = 'unknown'


def string_to_track_type(type_str: str) -> MkvTrackType:
    """
    Converts a string track type to the corresponding MkvTrackType enum value.
    Returns MkvTrackType.UNKNOWN if no matching value is found.
    """
    type_str = type_str.lower() if isinstance(type_str, str) else ""

    for track_type in MkvTrackType:
        if track_type.value == type_str:
            return track_type
    return MkvTrackType.UNKNOWN


@dataclass
class MkvTrack:
    """Track information of an MKV file."""
    codec: str
    id: int
    properties: MkvTrackProperties
    type: MkvTrackType


@dataclass
class MkvInfo:
    """Main class for MKV file information from mkvmerge -J."""
    file_name: str
    # identification_format_version: int
    container: MkvContainer
    tracks: List[MkvTrack]
    chapters: List[MkvChapter] = field(default_factory=list)
    attachments: List[Any] = field(default_factory=list)
    global_tags: List[Any] = field(default_factory=list)
    track_tags: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def parse_mkv_info(info_dict: Dict) -> MkvInfo:
    """
    Parses the JSON information of an MKV file into an MkvInfo instance.
    Handles missing fields gracefully by using default values.

    Args:
        info_dict: Dictionary with MKV information from mkvmerge -J

    Returns:
        MkvInfo object with typed metadata
    """
    # Process container properties
    container_props_dict = info_dict.get('container', {}).get('properties', {})
    known_props, _unknown_props = split_known_unknown_fields(container_props_dict, MkvContainerProperties)
    container_props = MkvContainerProperties(**known_props)
    #add_dynamic_attributes(container_props, unknown_props)

    # Create container
    container_dict = info_dict.get('container', {})
    container = MkvContainer(
        properties=container_props,
        recognized=container_dict.get('recognized', False),
        supported=container_dict.get('supported', False),
        type=container_dict.get('type', 'Unknown')
    )

    # Process tracks
    tracks: list = []
    for track_dict in info_dict.get('tracks', []):
        # Create track properties
        track_props_dict = track_dict.get('properties', {})
        known_track_props, _unknown_track_props = split_known_unknown_fields(track_props_dict, MkvTrackProperties)
        track_props = MkvTrackProperties(**known_track_props)
        #add_dynamic_attributes(track_props, unknown_track_props)

        # Create track with automatic track type conversion
        track = MkvTrack(
            codec=track_dict.get('codec', 'Unknown'),
            id=track_dict.get('id', 0),
            properties=track_props,
            type=string_to_track_type(track_dict.get('type', 'unknown'))
        )
        tracks.append(track)

    # Process chapters - handle case where chapter entries might have different structure
    chapters: list = []
    for chapter_dict in info_dict.get('chapters', []):
        try:
            chapters.append(MkvChapter(**chapter_dict))
        except (TypeError, ValueError) as e:
            # Log or handle malformed chapter entries
            print(f"Warning: Could not parse chapter entry: {e}")

    # Create main object
    return MkvInfo(
        file_name=info_dict.get('file_name', 'Unknown'),
        # identification_format_version=info_dict.get('identification_format_version', 0),
        container=container,
        tracks=tracks,
        chapters=chapters,
        attachments=info_dict.get('attachments', []),
        errors=info_dict.get('errors', []),
        global_tags=info_dict.get('global_tags', []),
        track_tags=info_dict.get('track_tags', []),
        warnings=info_dict.get('warnings', [])
    )
