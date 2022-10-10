import csv


def get_format_from_csv(file_path):
    """
    Gets the delimiter and quotechar from current CSV
    Parameters
    -------------
    file_path
        File path
    Returns
    -------------
    csv_dialect
        CSV dialect object
    """
    csv_dialect = None
    try:
        sample_bytes = 1024
        sniffer = csv.Sniffer()
        csv_dialect = sniffer.sniff(
            open(file_path).read(sample_bytes))
    except:
        sample_bytes = 16
        sniffer = csv.Sniffer()
        csv_dialect = sniffer.sniff(
            open(file_path).read(sample_bytes))

    return csv_dialect