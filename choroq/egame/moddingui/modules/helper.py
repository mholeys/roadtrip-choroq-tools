import choroq.read_utils as U

class Helper:
    @staticmethod
    def find_offsets(stream):
        offsets = [U.readLong(stream)]
        read_more = True
        while read_more:
            offset = U.readLong(stream)
            if offset < offsets[-1] or offset == 0 or stream.tell() >= offsets[0]:
                read_more = False
                break
            offsets.append(offset)

        return offsets