
import numpy as np
import copy
import os


# Function: get_way_data_from_file
#
# Gets chunks of data about an individual way from an osm file
#
# Parameters:
#
#    id - id of the target way
#    osm_file - osm file to get data from
#
# Returns:
#
#    metadata - The header
#    data - The list of nodes
#    end - Any lines after the nodes
#    index - The line in the osm file that it is located at
#
def get_way_data_from_file(id, osm_file):
    # <way id="$id" ...
    # metadata, just copy
    # <nd ref=" ...
    # data, copy line by line
    # </way>

    start_target = f"<way id=\"{id}\""
    data_target = "<nd ref="
    end_target = "</way>"
    state = 0
    metadata = []
    data = []
    end = []

    with open(osm_file) as f:
        for i, line in enumerate(f):
            line_stripped = line.strip()
            if state == 0 and line_stripped[0:len(start_target)] == start_target:
                state = 1
                metadata += [line]
            elif state == 1:
                if line_stripped[0:len(data_target)] == data_target:
                    state = 2
                    data += [line]
                else:
                    metadata += [line]
            elif state == 2:
                if line_stripped[0:len(end_target)] == end_target:
                    end += [line]
                    index = i
                    return metadata, data, end, index
                else:
                    data += [line]
    return None, None, None, None


def make_way_dashed(way_id, osm_file):
    target = f'<way id=\"{way_id}\" action=\"modify\" visible=\"true\" version=\"1\">'
    dashed_tag = f'dashed'

    with open(osm_file) as f:
        contents = f.readlines()

    for i, line in enumerate(contents):
        if (line.strip())[0:len(target)] == target:
            contents[i+2] = replace_substring(contents[i+2], dashed_tag, num_to_skip=2)
            break

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(contents)


def make_ways_dashed(osm_file, way_list=None):
    if way_list is None:
        way_list = []
        print('Enter ways to make dashed, type stop to process them')
        while True:
            _ = input()
            if _.lower() == 'stop':
                break
            else:
                way_list.append(_)

    for way_id in way_list:
        make_way_dashed(way_id, osm_file)


def get_lat_lon_from_point(id, osm_file):

    target = f"<node id=\"{id}\" action=\"modify\" visible=\"true\" version=\"1\" lat=\""

    with open(osm_file) as f:
        for i, line in enumerate(f):
            line_stripped = line.strip()
            if line_stripped[0:len(target)] == target:
                lat_start = len(target)
                lat_end = line_stripped.index("\"", lat_start)
                lon_start = line_stripped.index("\"", lat_end+1)+1
                lon_end = line_stripped.index("\"", lon_start)
                lat = float(line_stripped[lat_start:lat_end])
                lon = float(line_stripped[lon_start:lon_end])
                return lat, lon
    return None, None


def change_lanelet_boundary(lanelet, current_boundary, updated_boundary, osm_file):

    start_target = f"<relation id=\"{lanelet}\" action=\"modify\" visible=\"true\" version=\"1\">"
    data_target = f"<member type=\"way\" ref=\"{current_boundary}"
    boundary_metadata_left = "<member type=\"way\" ref=\""
    boundary_metadata_right = "\" role=\"right\"/>"
    state = 0

    with open(osm_file) as f:
        for i, line in enumerate(f):
            line_stripped = line.strip()
            if state == 0 and line_stripped == start_target:
                # Found the lanelet, now we need to check the lanelet boundaries
                state = 1
            elif state == 1:
                if line_stripped[0:len(data_target)] == data_target:
                    boundary_metadata_left = line[:line.index(boundary_metadata_left)] + boundary_metadata_left
                    boundary_metadata_right = line[len(boundary_metadata_left) + len(str(current_boundary)):]
                    new_line = boundary_metadata_left + str(updated_boundary) + boundary_metadata_right
                    return new_line, i
                else:
                    state = 2
            elif state == 2:
                if line_stripped[0:len(data_target)] == data_target:
                    boundary_metadata_left = line[:line.index(boundary_metadata_left)] + boundary_metadata_left
                    boundary_metadata_right = line[len(boundary_metadata_left) + len(str(current_boundary)):]
                    new_line = boundary_metadata_left + str(updated_boundary) + boundary_metadata_right
                    return new_line, i
                else:
                    return None, None

    return None, None


def get_lat_lon_from_data_line(line, osm_file):
    id = line[line.index("\"") + 1:line.rindex("\"")]
    lat_lon = get_lat_lon_from_point(id, osm_file)
    return lat_lon


def compute_lanelet_boundary_angle(data_lines, osm_file):
    data_center1 = data_lines[(len(data_lines) - 1) // 2]
    lat_1, lon_1 = get_lat_lon_from_data_line(data_center1, osm_file)
    data_center2 = data_lines[(len(data_lines) - 1) // 2 + 1]
    lat_2, lon_2 = get_lat_lon_from_data_line(data_center2, osm_file)
    angle = np.arctan2(lat_2 - lat_1, lon_2 - lon_1)
    return angle


def replace_substring(string, substring, start_char="\"", end_char="\"", num_to_skip=0):
    start = 0
    for _ in range(num_to_skip):
        start = string.index(start_char, start) + 1

    substr_start = string.index(start_char, start) + 1
    substr_end = string.index(end_char, substr_start)
    # string[substr_start:substr_end] = substring
    updated_string = string[:substr_start] + substring + string[substr_end:]
    return updated_string


def get_substring(string, start_char="\"", end_char="\"", num_to_skip=0):
    start = 0
    for _ in range(num_to_skip):
        start = string.index(start_char, start) + 1

    substr_start = string.index(start_char, start) + 1
    substr_end = string.index(end_char, substr_start)
    return string[substr_start:substr_end]


# def replace_substring(string, replacee, replacer):
#     i = string.index(replacee)
#     new_string = string[:i] + replacer + string[i + len(replacee):]
#     return new_string


# Given a doubled lanelet boundary, get the lanelets associated with it and the other boundary of each
def get_boundaries_lanelets_from_doubled_boundary(doubled_boundary, osm_file):

    lanelet_target = f"<relation id=\""
    doubled_boundary_target = f"<member type=\"way\" ref=\"{doubled_boundary}\""
    doubled_data = [int(doubled_boundary)]

    with open(osm_file) as f:
        contents = f.readlines()

    for i, line in enumerate(contents):
        line_stripped = line.strip()
        if line_stripped[0:len(doubled_boundary_target)] == doubled_boundary_target:
            # We have a lanelet and other boundary
            # Either it is Lanelet -> this -> other boundary, or Lanelet -> other boundary -> this
            # Check if it's Lanelet -> this -> other boundary
            if (contents[i-1].strip())[0:len(lanelet_target)] == lanelet_target:
                # This is the lanelet
                doubled_data.append(int(get_substring(contents[i - 1])))
                # This is the other boundary
                doubled_data.append(int(get_substring(contents[i + 1], num_to_skip=2)))
            else:
                # This is the lanelet
                doubled_data.append(int(get_substring(contents[i - 2])))
                # This is the other boundary
                doubled_data.append(int(get_substring(contents[i - 1], num_to_skip=2)))

        if len(doubled_data) >= 5:
            return doubled_data

    return None


def get_doubled_centerlines(osm_file):
    # dict = {}
    # with open("/home/alex/Downloads/xodr/McLean_Loop.osm") as infile:
    #     infile.readline()

    target = "<member type=\"way\" ref=\""

    with open(osm_file) as f:
        seen = set()
        prior = ""
        twoprior = ""
        dupes = 0
        doubled_boundary_datas = []
        for line in f:
            try:
                start_index = line.index(target) + len(target)
                end_index = line.index("\"", len(line) - 5)
                to_check = line[start_index:end_index]
                # if to_check[0:6] == "117711":
                #     print('hi')
                if to_check in seen:
                    # print(twoprior, end="")
                    # print(prior, end="")
                    # print(line, end="")
                    # print()
                    dupes += 1
                    doubled_boundary = get_substring("\"" + to_check)
                    doubled_boundary_data = get_boundaries_lanelets_from_doubled_boundary(doubled_boundary, osm_file)
                    doubled_boundary_datas.append(doubled_boundary_data)
                else:
                    seen.add(to_check)
            except:
                tmp = 2
            twoprior = prior
            prior = line
    print(dupes)
    return doubled_boundary_datas


# doubled_boundaries:
#   [ id of doubled boundary
#     id of lanelet 1
#     id of other boundary of lanelet 1
#     id of lanelet 2
#     id of other boundary of lanelet 2 ]
# osm_map:
#   string, absolute path to the osm file
def fix_doubled_centerlines(doubled_boundaries, osm_file):

    # Grab the error lanelet associated with the boundary
    #   Get the direction of this boundary
    #       Grab the center point, or very near there
    #       dir = atan2(y2-y1, x2-x1)
    #   Get the direction of each associated lanelet
    #       Get the other 2 lanelet boundaries
    #           Get the 2 lanelets associated with this boundary
    #           Get the other boundary assocated with each lanelet
    #       dir = atan2(y2-y1, x2-x1)
    #   The odd one out is the error lanelet/boundary
    #       compute diffs to doubled, the larger one is associated with the error lanelet
    # Create a reversed copy of the boundary, associated with the error lanelet
    #   Copy the metadata
    #   Copy and reverse the points

    # new_osm = osm_file[:-4] + '_fixed.osm'

    for doubled_boundary_data in doubled_boundaries:
        # Grab the error lanelet associated with the boundary
        [doubled_boundary, lanelet1, lanelet1_boundary, lanelet2, lanelet2_boundary] = doubled_boundary_data
        #   Get the direction of this boundary
        #       Grab the center point, or very near there
        #       dir = atan2(y2-y1, x2-x1)
        metadata, data, end, index = get_way_data_from_file(doubled_boundary, osm_file)
        dir_doubled = compute_lanelet_boundary_angle(data, osm_file)
        #   Get the direction of each associated lanelet
        #       Get the other 2 lanelet boundaries
        #           Get the 2 lanelets associated with this boundary
        #           Get the other boundary assocated with each lanelet
        #       dir = atan2(y2-y1, x2-x1)
        metadata1, data1, end1, _ = get_way_data_from_file(lanelet1_boundary, osm_file)
        dir_1 = compute_lanelet_boundary_angle(data1, osm_file)
        metadata2, data2, end2, _ = get_way_data_from_file(lanelet2_boundary, osm_file)
        dir_2 = compute_lanelet_boundary_angle(data2, osm_file)
        #   The odd one out is the error lanelet/boundary
        #       compute diffs to doubled, the larger one is associated with the error lanelet
        diff_1 = abs(dir_1 - dir_doubled)
        diff_2 = abs(dir_2 - dir_doubled)
        if diff_1 >= diff_2:
            # It's lanelet 1 and boundary
            print(lanelet1)
            lanelet_to_update = lanelet1
            boundary_to_update = lanelet1_boundary
        else:
            # It's lanelet 2 and boundary
            print(lanelet2)
            lanelet_to_update = lanelet2
            boundary_to_update = lanelet2_boundary

        # Create a reversed copy of the boundary, associated with the error lanelet
        #   Copy the metadata
        #   Copy and reverse the points
        with open(osm_file) as f:
            contents = f.readlines()

        start_index = index + 1
        flipped_data = list(np.flip(data))
        edited_boundary_id = int(str(doubled_boundary) + '99')
        metadata[0] = replace_substring(metadata[0], str(edited_boundary_id))
        data_list = metadata + flipped_data + end

        updated_line, index = change_lanelet_boundary(lanelet_to_update, doubled_boundary, edited_boundary_id, osm_file)
        contents[index] = updated_line

        for i, data in enumerate(data_list):
            contents.insert(start_index + i, data)

        os.remove(osm_file)
        with open(osm_file, "a+") as f:
            f.writelines(contents)

    print('done')


def reverse_way(lanelet_id, way_id, osm_file, create_new=False):
    metadata, data, end, index = get_way_data_from_file(way_id, osm_file)

    # Create a reversed copy of the boundary, associated with the error lanelet
    #   Copy the metadata
    #   Copy and reverse the points
    with open(osm_file) as f:
        contents = f.readlines()

    start_index = index + 1
    flipped_data = list(np.flip(data))

    if create_new:
        edited_boundary_id = int(str(way_id) + '99')
        metadata[0] = replace_substring(metadata[0], str(edited_boundary_id))
        data_list = metadata + flipped_data + end
        updated_line, index = change_lanelet_boundary(lanelet_id, way_id, edited_boundary_id, osm_file)

    data_list = metadata + flipped_data + end
    updated_line, index = change_lanelet_boundary(lanelet_id, way_id, way_id, osm_file)
    contents[index] = updated_line

    for i, data in enumerate(data_list):
        contents.insert(start_index + i, data)

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(contents)


def reverse_lanelets(osm_file, lanelet_list=None):

    if lanelet_list is None:
        lanelet_list = []
        print('Enter lanelets, type stop to process them')
        while True:
            _ = input()
            if _.lower() == 'stop':
                break
            else:
                lanelet_list.append(_)
    elif lanelet_list == 'all':
        lanelet_list = get_all_lanelets_from_file(osm_file)

    ways = {}
    for lanelet_id in lanelet_list:
        way1, way2 = get_ways_from_lanelet(lanelet_id, osm_file)
        ways[str(way1)] = lanelet_id
        ways[str(way2)] = lanelet_id

    for way in ways.keys():
        try:
            reverse_way(ways[way], int(way), osm_file)
        except:
            print(f'got bad lanelet, I think: {way} - {ways[way]}')


def get_ways_from_lanelet(lanelet_id, osm_file):
    start_target = f"<relation id=\"{lanelet_id}\" action=\"modify\" visible=\"true\" version=\"1\">"

    with open(osm_file) as f:
        contents = f.readlines()

    for i, line in enumerate(contents):
        line_stripped = line.strip()
        if line_stripped == start_target:
            way1_id = get_substring(contents[i + 1], num_to_skip=2)
            way2_id = get_substring(contents[i + 2], num_to_skip=2)

            return way1_id, way2_id

    print(f'problems finding lanelet {lanelet_id}')
    return None, None


def grab_start_and_end_points_from_way(way_id, osm_file):
    metadata, data, end, index = get_way_data_from_file(way_id, osm_file)
    return data[0], data[-1]


def globally_replace_point_return_contents(replacer, replacee, contents):

    target = f"<nd ref=\"{replacee}\""
    delete_target = f"<node id=\"{replacee}\""

    # with open(osm_file) as f:
    #     contents = f.readlines()

    for i, line in enumerate(contents):
        if (line.strip())[0:len(delete_target)] == delete_target:
            del contents[i]
            break

    for i, line in enumerate(contents):
        if (line.strip())[0:len(target)] == target:
            contents[i] = replace_substring(line, str(replacer))

    # os.remove(osm_file)
    # with open(osm_file, "a+") as f:
    #     f.writelines(contents)
    return contents


def globally_replace_point(replacer, replacee, osm_file):

    target = f"<nd ref=\"{replacee}\""
    delete_target = f"<node id=\"{replacee}\""
    data_list = []

    with open(osm_file) as f:
        contents = f.readlines()

    for i, line in enumerate(contents):
        if (line.strip())[0:len(delete_target)] == delete_target:
            del contents[i]
            break

    for i, line in enumerate(contents):
        if (line.strip())[0:len(target)] == target:
            contents[i] = replace_substring(line, str(replacer))

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(contents)


def check_lanelets_for_route(lanelet_list, osm_file, route_file):

    if lanelet_list is None:
        lanelet_list = []
        print('Enter lanelets, type stop to process them')
        while True:
            _ = input()
            if _.lower() == 'stop':
                break
            else:
                lanelet_list.append(_)

    with open(route_file) as f:
        contents = f.readlines()

    translated_last = -1
    untranslated_last = 'INVALID'
    for lanelet in lanelet_list:
        table_target = f"[label=\"{lanelet}\" lanelet=\"{lanelet}\"];"
        for i, line in enumerate(contents):
            if (line.strip())[len(line) - len(table_target) - 1:] == table_target:
                translated = line[0:len(line) - len(table_target) - 1]
                print(f'lanelet {lanelet} is {translated}')
                target = f"{translated_last}->{translated}"
                print(f"Checking {target}")
                found = False
                for j, line2 in enumerate(contents):
                    if (line2.strip())[0:len(target)] == target:
                        found = True
                        print(line2, end='')
                if not found and untranslated_last != 'INVALID':
                    print(f'-----------------{untranslated_last}->{lanelet} Not found------------------')
                    # way1, way2 = grab_ways_from_lanelet(untranslated_last, osm_file)
                    # print(grab_start_and_end_points_from_way(way1, osm_file))
                    # print(grab_start_and_end_points_from_way(way2, osm_file))
                    #
                    # way1, way2 = grab_ways_from_lanelet(lanelet, osm_file)
                    # print(grab_start_and_end_points_from_way(way1, osm_file))
                    # print(grab_start_and_end_points_from_way(way2, osm_file))
                    #
                    # replacer = int(input('Enter point to replace it with: '))
                    # replacee = int(input('Enter point to be replaced: '))
                    # globally_replace_point(replacer, replacee, osm_file)
                    # print()
                translated_last = translated
                untranslated_last = lanelet


def deduplicate_points(osm_file):

    target = "<node id=\""

    with open(osm_file) as f:
        contents = f.readlines()

    edited_contents = contents.copy()
    seen = {}
    dupes = 0
    for i, line in enumerate(contents):
        if (line.strip())[0:len(target)] == target:
            id = int(get_substring(line, num_to_skip=0))
            lat = get_substring(line, num_to_skip=8)
            lon = get_substring(line, num_to_skip=10)
            key = f"{lat}_{lon}"
            if key in seen.keys():
                print(f'line: {i}, id: {id}')
                dupes += 1
                edited_contents = globally_replace_point_return_contents(seen[key], id, edited_contents)
            else:
                seen[key] = id

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(edited_contents)

    print(dupes)
    print(i)
    return


def remove_orphaned_points(osm_file):

    node_definition = "<node id=\""
    used_in_way = "<nd ref=\""

    with open(osm_file) as f:
        contents = f.readlines()

    seen = {}
    for i, line in enumerate(contents):
        if (line.strip())[0:len(node_definition)] == node_definition:
            id = int(get_substring(line, num_to_skip=0))
            key = f"{id}"
            seen[key] = -1

    for i, line in enumerate(contents):
        if (line.strip())[0:len(used_in_way)] == used_in_way:
            id = int(get_substring(line, num_to_skip=0))
            key = f"{id}"
            seen[key] = int(key)
    print(len(contents))
    offset = 0
    for i in range(len(contents)):
        i += offset
        line = contents[i]
        if (line.strip())[0:len(node_definition)] == node_definition:
            id = int(get_substring(line, num_to_skip=0))
            key = f"{id}"
            if seen[key] == -1:
                del contents[i]
                offset -= 1
    print(len(contents))

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(contents)
    return


def remove_lanelets_except(osm_file, lanelets_to_keep=None):
    target = f"<relation id=\""
    lanelet_line_2 = f"<member type=\""
    regulatory_line_2 = f"<tag k=\"type\" v=\"regulatory_element\"/>"

    if lanelets_to_keep is None:
        lanelets_to_keep = []
        print('Enter lanelets to keep, type stop to process them')
        while True:
            _ = input()
            if _.lower() == 'stop':
                break
            else:
                lanelets_to_keep.append(_)

    with open(osm_file) as f:
        contents = f.readlines()

    '''
      <relation id="274" action="modify" visible="true" version="1">
        <tag k="type" v="regulatory_element"/>
        <tag k="subtype" v="digital_speed_limit"/>
        <tag k="limit" v="70 mph"/>
        <tag k="participant:vehicle" v="yes"/>
        <member type="relation" ref="273" role="refers"/>
      </relation>
    '''

    all_lanelets = []
    for i, line in enumerate(contents):
        if (line.strip())[0:len(target)] == target:
            if (contents[i+1].strip())[0:len(lanelet_line_2)] == lanelet_line_2:
                lanelet_id = int(get_substring(line, num_to_skip=0))
                all_lanelets.append(lanelet_id)
            if (contents[i+1].strip())[0:len(regulatory_line_2)] == regulatory_line_2:
                ref_line = contents[i+5].strip()
                ref = int(get_substring(ref_line, num_to_skip=2))
                if str(ref) not in lanelets_to_keep:
                    lanelet_id = int(get_substring(line, num_to_skip=0))
                    all_lanelets.append(lanelet_id)

    print(f'total num lanelets {len(all_lanelets)}, num to keep is {len(lanelets_to_keep)}')
    delta = len(all_lanelets) - len(lanelets_to_keep)
    count = 0

    for lanelet in all_lanelets:
        if str(lanelet) not in lanelets_to_keep:
            remove_lanelet(lanelet, osm_file, False)
            count += 1
            if count % (delta // 10) == 0:
                print(f'{count / delta * 100} percent complete')

    remove_orphaned_points(osm_file)
    return


def remove_lanelet(lanelet_id, osm_file, remove_orphans=True):
    # remove the lanelet definition and the two boundary ways, then call remove_orphaned_points to clean up the rest.'
    way1, way2 = get_ways_from_lanelet(lanelet_id, osm_file)

    with open(osm_file) as f:
        contents = f.readlines()

    remove_way(way1, contents)
    remove_way(way2, contents)
    remove_lanelet_header(lanelet_id, contents)

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(contents)

    if remove_orphans:
        remove_orphaned_points(osm_file)
    return


def remove_lanelet_header(lanelet_id, contents):
    delete_target = f"<relation id=\"{lanelet_id}\""
    end_target = "</relation>"

    for i, line in enumerate(contents):
        line_stripped = line.strip()
        if line_stripped[0:len(delete_target)] == delete_target:
            del contents[i]
            while True:
                line_stripped = contents[i].strip()
                if line_stripped[0:len(end_target)] == end_target:
                    del contents[i]
                    break
                else:
                    del contents[i]

    return contents


def remove_points(points, osm_file):
    for point in points:
        remove_point(point, osm_file)


def remove_point(point_id, osm_file):
    definition_target = f"<node id=\"{point_id}\""
    use_target = f"<nd ref=\"{point_id}\""

    with open(osm_file) as f:
        contents = f.readlines()

    for i, line in enumerate(contents):
        if (line.strip())[0:len(definition_target)] == definition_target\
                or (line.strip())[0:len(use_target)] == use_target:
            del contents[i]
            print(f'removed {point_id}')
            # break

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(contents)


def remove_way(way_id, contents):

    delete_target = f"<way id=\"{way_id}\""
    end_target = "</way>"

    for i, line in enumerate(contents):
        line_stripped = line.strip()
        if line_stripped[0:len(delete_target)] == delete_target:
            del contents[i]
            while True:
                line_stripped = contents[i].strip()
                if line_stripped[0:len(end_target)] == end_target:
                    del contents[i]
                    break
                else:
                    del contents[i]

    return contents


def globally_replace_way_return_contents(replacer, replacee, contents):

    target = f"<member type=\"way\" ref=\"{replacee}\""

    contents = remove_way(replacee, contents)

    for i, line in enumerate(contents):
        if (line.strip())[0:len(target)] == target:
            contents[i] = replace_substring(line, str(replacer), num_to_skip=2)

    return contents


def deduplicate_ways(osm_file):

    target = "<way id=\""

    with open(osm_file) as f:
        contents = f.readlines()

    edited_contents = contents.copy()
    seen = {}
    dupes = 0
    for i, line in enumerate(contents):
        if (line.strip())[0:len(target)] == target:
            way_id = int(get_substring(line, num_to_skip=0))
            first, last = grab_start_and_end_points_from_way(way_id, osm_file)
            key = f"{first}_{last}"
            if key in seen.keys():
                print(f'line: {i}, id: {way_id}')
                dupes += 1
                edited_contents = globally_replace_way_return_contents(seen[key], way_id, edited_contents)
            else:
                seen[key] = way_id

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(edited_contents)

    print(dupes)
    print(i)
    return


def get_all_lanelets_from_file(osm_file):
    target = f"<relation id=\""
    lanelet_line_2 = f"<member type=\""

    with open(osm_file) as f:
        contents = f.readlines()

    lanelet_ids = []
    for i, line in enumerate(contents):
        line_stripped = line.strip()
        if line_stripped[0:len(target)] == target:
            if (contents[i+1].strip())[0:len(lanelet_line_2)] == lanelet_line_2:
                lanelet_id = int(get_substring(line_stripped, num_to_skip=0))
                lanelet_ids.append(lanelet_id)

    return lanelet_ids


def compute_way_length_from_file(osm_file, way, lat_to_m, lon_to_m):
    # print(f'starting way {way}')
    distance = 0
    too_close = []

    metadata, data, end, index = get_way_data_from_file(way, osm_file)
    distances = np.zeros(len(data))

    last_point = int(get_substring(data[0], num_to_skip=0))
    last_lat, last_lon = get_lat_lon_from_point(last_point, osm_file)
    for i in range(len(data) // 2):
        point_text = data[i]
        point = int(get_substring(point_text, num_to_skip=0))
        lat, lon = get_lat_lon_from_point(point, osm_file)

        delta_m_lat = lat_to_m * (lat - last_lat)
        delta_m_lon = lon_to_m * (lon - last_lon)
        dist_step = np.sqrt(delta_m_lat**2 + delta_m_lon**2)

        if i > 0:
            if dist_step < 2.0:
                too_close.append(point)
            else:
                distance += dist_step
                distances[i] = dist_step
                last_lat, last_lon = lat, lon

    last_point = int(get_substring(data[-1], num_to_skip=0))
    last_lat, last_lon = get_lat_lon_from_point(last_point, osm_file)
    for i in range(len(data) - 1, len(data) // 2 - 2, -1):
        point_text = data[i]
        point = int(get_substring(point_text, num_to_skip=0))
        lat, lon = get_lat_lon_from_point(point, osm_file)

        delta_m_lat = lat_to_m * (lat - last_lat)
        delta_m_lon = lon_to_m * (lon - last_lon)
        dist_step = np.sqrt(delta_m_lat ** 2 + delta_m_lon ** 2)

        if i < len(data) - 1:
            if dist_step < 2.0:
                too_close.append(point)
            else:
                distance += dist_step
                distances[i] = dist_step
                last_lat, last_lon = lat, lon

    return distance, distances, too_close


def get_largest_id_from_file(osm_file):
    # relation id
    # node id
    # way id
    target1 = f"<node id=\""
    target2 = f"<way id=\""
    target3 = f"<relation id=\""
    target4 = "<member type=\"relation\" ref=\""

    with open(osm_file) as f:
        contents = f.readlines()

    max = 0
    for i, line in enumerate(contents):
        line_stripped = line.strip()
        if line_stripped[0:len(target1)] == target1\
                or line_stripped[0:len(target2)] == target2\
                or line_stripped[0:len(target3)] == target3:
            id = int(get_substring(line_stripped, num_to_skip=0))
            if id > max:
                max = id
        elif line_stripped[0:len(target4)] == target4:
            id = int(get_substring(line_stripped, num_to_skip=2))
            if id > max:
                max = id

    return max


# Currently just prints the lanelets that need to be split, along with the specicific node(s) to split it on
def split_lanelet_by_dist_from_file(osm_file, lanelet, way1, way2, split_dist, lat_to_m, lon_to_m):

    max_id = get_largest_id_from_file(osm_file)
    way1_length, way1_dists, _ = compute_way_length_from_file(osm_file, way1, lat_to_m, lon_to_m)
    way2_length, way2_dists, _ = compute_way_length_from_file(osm_file, way2, lat_to_m, lon_to_m)
    metadata1, data1, end1, index1 = get_way_data_from_file(way1, osm_file)
    metadata2, data2, end2, index2 = get_way_data_from_file(way2, osm_file)

    # compute split target path lengths (keep them reasonably the same length)
    splits = int(way1_length // split_dist) + 1
    if splits > 0 and splits % way1_length < (split_dist // 3):  # Allow the lanelets to be a smidge longer
        splits -= 1
    length = way1_length / splits

    data1 = np.array(data1)
    data2 = np.array(data2)
    length_indices = []
    for i in range(splits):
        sum_dist = 0
        for j, incremental_dist in enumerate(way1_dists):
            sum_dist += incremental_dist
            if sum_dist > length * (i+1):
                length_indices.append(j)
                break

    print(f'way: {way1}, splits: {data1[length_indices]}')
    print(f'way: {way2}, splits: {data2[length_indices]}')
    print(f'associated lanelet: {lanelet}')
    print(f'starting id for new lanelets/ways: {max_id}')

    # create list of [header, points, footer]
    # 

    # get list of way1 and way2 points
    # walk along way1 to reach each split length, then record the index
    # split each way into an array of [last point of prior, other...points, last point]
    #
    # for each split:
        # if 0, return
        # create a new lanelet
        # lanelet 1:
            # create a new way
            # Fill it with split[0] - 1 to split[1] points
            #
    # for each way:
    # create # splits new lanelets, with numbers starting after the largest number in the file
    # grab the first point after each path length is reached
    #from the first lanelet, remove the excess points
    # for each split:
        # create the header, then add the remaining points, and the end point
        # create a new relation
    # put the

    # distance = 0
    # distances = []
    #
    # metadata, data, end, index = get_way_data_from_file(way, osm_file)
    #
    # last_point = int(get_substring(data[0], num_to_skip=0))
    # last_lat, last_lon = get_lat_lon_from_point(last_point, osm_file)
    # for i, point_text in enumerate(data):
    #     point = int(get_substring(point_text, num_to_skip=0))
    #     lat, lon = get_lat_lon_from_point(point, osm_file)
    #
    #     delta_m_lat = lat_to_m * (lat - last_lat)
    #     delta_m_lon = lon_to_m * (lon - last_lon)
    #     dist_step = np.sqrt(delta_m_lat**2 + delta_m_lon**2)
    #
    #     distance += dist_step
    #     distances.append(dist_step)
    #     last_lat, last_lon = lat, lon
    #
    # return distance, distances


def compute_lanelet_length(osm_file, lat, lon, lanelets=None):
    # lat_to_m, earth is 40000000m in diameter, and 360 degrees (10000000m and 90 degrees to simplify)
    # lat_to_m = 90/10000000 = 0.000009
    # delta_m_lat = delta_lat * lat_to_m
    # lon_to_m is dependent on latitude. lon_circumference = 40000000 * cos(lat)
    # lon_to_m = 90/(10000000 * cos(lat))
    # delta_m_lon = delta_lon * lon_to_m
    # delta_m = sqrt(delta_m_lat**2 + delta_m_lon**2)
    lat_to_m = 10000000.0/90.0
    lon_to_m = (10000000.0 * np.cos(lat * np.pi/180))/90.0

    # get list of lanelets
    # for each lanelet
        # get both boundaries
        # use lat/lon gps to m to compute the length between each point in each boundary
        # average the length of the two boundaries, and return that length

    # get list of lanelets
    lanelets = get_all_lanelets_from_file(osm_file)
    close_points = {}

    # for each lanelet
    for lanelet in lanelets:
        # get both boundaries
        way1, way2 = get_ways_from_lanelet(lanelet, osm_file)
        # use lat/lon gps to m to compute the length between each point in each boundary
        d1, steps1, close1 = compute_way_length_from_file(osm_file, way1, lat_to_m, lon_to_m)
        d2, steps2, close2 = compute_way_length_from_file(osm_file, way2, lat_to_m, lon_to_m)
        if len(close1) > 0 or len(close2) > 0:
            print('small')
            for i in range(len(close1)):
                # print(f'point {close1[i]}, from way {way1}, lanelet {lanelet}, distance < 0.25')
                close_points[close1[i]] = way1
            for i in range(len(close2)):
                # print(f'point {close2[i]}, from way {way2}, lanelet {lanelet}, distance < 0.25')
                close_points[close2[i]] = way1
        distance = (d1 + d2) / 2
        splits = int(distance // 150)
        if splits > 0 and distance % 150 < 50:
            splits -= 1
        print(f'lanelet {lanelet} is {int(distance)} m, recommend {splits} splits')
        if splits > 0:
            split_lanelet_by_dist_from_file(osm_file, lanelet, way1, way2, 150, lat_to_m, lon_to_m)
        # average the length of the two boundaries, and return that length
    print()
    for point in close_points.keys():
        print(f'{point}')
    return close_points


def set_fixed_offset(osm_file, offset_x=0.0, offset_y=0.0, offset_lat=None, offset_lon=None, lat=28.1185796):
    if offset_lat is None:
        offset_lat = offset_y * (90.0 / 10000000.0)
    if offset_lon is None:
        offset_lon = offset_x * (90.0 / (10000000.0 * np.cos(np.pi/180 * lat)))
    print(f'{offset_lat}, {offset_lon}')

    target = f'<geoReference>'
    node_target = f'<node id=\"'
    # <geoReference>+proj=tmerc +lat_0=28.11857965984839 +lon_0=-81.83067386240469 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +geoidgrids=egm96_15.gtx +vunits=m +no_defs </geoReference>
    # <node id='1' action='modify' visible='true' version='1' lat='28.12460546908' lon='-81.82879471276' />

    with open(osm_file) as f:
        contents = f.readlines()

    for i, line in enumerate(contents):
        if (line.strip())[0:len(target)] == target:
            lat = float(get_substring(line.strip(), '=', ' ', num_to_skip=1))
            lat += offset_lat
            line = replace_substring(line, str(lat), '=', ' ', num_to_skip=1)
            lon = float(get_substring(line.strip(), '=', ' ', num_to_skip=2))
            lon += offset_lon
            line = replace_substring(line, str(lon), '=', ' ', num_to_skip=2)
            contents[i] = line
        elif (line.strip())[0:len(node_target)] == node_target:
            lat = float(get_substring(line.strip(), num_to_skip=8))
            lat += offset_lat
            line = replace_substring(line, str(lat), num_to_skip=8)
            lon = float(get_substring(line.strip(), num_to_skip=10))
            lon += offset_lon
            line = replace_substring(line, str(lon), num_to_skip=10)
            contents[i] = line

    os.remove(osm_file)
    with open(osm_file, "a+") as f:
        f.writelines(contents)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    osm_file = "/home/alex/Downloads/TFHRC map/TFHRC_TIM_CCW_fixed_small_lanelets.osm"
    # osm_file = "/home/alex/Downloads/Suntrax_map/Suntrax_03.10.22_oval_only (copy).osm"
    # route_file = "/home/alex/carma_ws/src/carma-platform/route/routing_Suntrax.txt"

    # deduplicate_points(osm_file)

    # ENU: +lat = +y, +lon = -x
    # set_fixed_offset(osm_file, offset_x=-1.5, offset_y=1.5)
    set_fixed_offset(osm_file, offset_x=-2.85, offset_y=2.1)
    # Add 1.5m at 20 degrees, move the car x 1.35, y -0.60, means move the map x -1.35, y 0.60
    # set_fixed_offset(osm_file, offset_x=-1.0, offset_y=1.0)



    # while True:
    #     lanelet_id = int(input('Enter lanenelet to print way data \n'))
    #     way1, way2 = grab_ways_from_lanelet(lanelet_id, osm_file)
    #     print(get_data_boundary(way1, osm_file))
    #     print(get_data_boundary(way2, osm_file))
    #     reverse_way(lanelet_id, way1, osm_file)
    #     reverse_way(lanelet_id, way2, osm_file)

    # max_id = get_largest_id_from_file(osm_file)
    # print(max_id)
    # close_points = compute_lanelet_length(osm_file, 28.11857965984839, -81.83067386240469)
    # print(close_points)
    #
    # for point in close_points.keys():
    #     remove_point(point, osm_file)

    # close_points_arr = [344, 650, 1263, 6249, 5937, 6348, 12956, 12923]
    # remove_points(close_points_arr, osm_file)
    # close_points_arr = [30473, 30474, 30291, 30292, 37317, 37318, 38120, 38121, 43098, 43097, 45534, 45535, 45409, 45410, 46410, 46409, 50402, 50403, 50647, 50646, 57242, 57241, 57240, 57158, 57359, 57358, 57357, 57275, 57503, 57504, 57505, 57589, 57585, 57584, 57766, 57767, 57768, 57894, 57849, 57626, 57627, 57754, 57709, 81511, 81510, 81307, 81306, 81923, 81922, 82545, 82546]
    # remove_points(close_points_arr, osm_file)
    # remove_lanelets_except(osm_file)
    # remove_orphaned_points(osm_file)
    # check_lanelets_for_route(None, osm_file, route_file)

    # To create an osm file from xodr:
    # https://github.com/usdot-fhwa-stol/opendrive2lanelet
    # cd ~/carma_ws/src/opendrive2lanelet
    # docker build -t opendrive2lanelet2convertor .
    # docker run --rm -it -v /home/alex/Downloads/Mclean_03-22-22_xodr/:/root/opendrive2lanelet/map opendrive2lanelet2convertor
    #   where /home/alex/Downloads/Mclean_03-22-22_xodr/ is the path to a folder containing the xodr file(s)

    # unit test instructions:
    # test_route_generator.cpp
    # Change filename and starting/ending lanelet
    # source /opt/ros/noetic/setup.bash
    # cd /workspaces/carma_ws/
    # colcon build --packages-select route --install-base install_ros1 --build-base build_ros1
    # colcon test --packages-select route --install-base install_ros1 --build-base build_ros1 --event-handlers console_cohesion+

    # Then you can also check out the route file at routing.txt
    # You can move that file into this directory, so that other functions can use it to check routability

    # while True:
    #     lanelet_id = int(input('Enter lanelet to analyze: '))
    #     way1, way2 = grab_ways_from_lanelet(lanelet_id, osm_file)
    #     print(grab_start_and_end_points_from_way(way1, osm_file))
    #     print(grab_start_and_end_points_from_way(way2, osm_file))
    #
    #     lanelet_id = int(input('Enter second lanelet to analyze: '))
    #     way1, way2 = grab_ways_from_lanelet(lanelet_id, osm_file)
    #     print(grab_start_and_end_points_from_way(way1, osm_file))
    #     print(grab_start_and_end_points_from_way(way2, osm_file))
    #
    #     replacer = int(input('Enter point to replace it with: '))
    #     replacee = int(input('Enter point to be replaced: '))
    #     globally_replace_point(replacer, replacee, osm_file)
    #     print('done')
    #     print()

    # doubled_boundaries = find_doubled_centerlines(osm_file)
    # fix_doubled_centerlines(doubled_boundaries, osm_file)
    print('done')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

# Glitch 180 from starting point, between out lane and gantry
