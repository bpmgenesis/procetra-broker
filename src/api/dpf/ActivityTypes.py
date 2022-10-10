from enum import Enum, auto

class ActivityTypes(Enum):
    Start = 'Start',
    End = 'End',
    ImportCsv = 'ImportCsv',
    SelectDataSource = 'SelectDataSource',
    LoadEventData = 'LoadEventData',
    DeleteDublucates = 'DeleteDublucates',
    ChangeCase = 'ChangeCase',
    JoinColumns = 'JoinColumns',
    ChangeType = 'ChangeType',
    CombineTimestamp = 'CombineTimestamp',
    CreateTimestamp = 'CreateTimestamp',
    DateDiff = 'DateDiff',
    DateAdd = 'DateAdd',
    Delete = 'Delete',
    DeriveField = 'DeriveField',
    RemoveSubstring = 'RemoveSubstring',
    ReplaceSubstring = 'ReplaceSubstring',
    RoundTimestamp = 'RoundTimestamp',
    Trim = 'Trim',
    MergeDataset = 'MergeDataset'