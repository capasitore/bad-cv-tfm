from model.badminton.court_model import BadmintonCourt
import numpy as np
import cv2
import itertools
import time


def euqlidean_distance(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.linalg.norm(a - b)


def triangle_area(a, b, c):
    # https://en.wikipedia.org/wiki/Shoelace_formula
    # http://math.stackexchange.com/questions/516219/finding-out-the-area-of-a-triangle-if-the-coordinates-of-the-three-vertices-are
    m = np.array([[a[0], b[0], c[0]], [a[1], b[1], c[1]], [1, 1, 1]])

    return (abs(np.linalg.det(m)) * 0.5)


class Line(object):

    def __init__(self,a,b,rho):
        self.a = a
        self.b = b
        self.rho = rho


class LineIntersection(object):
    def __init__(self, line_1, line_2,max_cols,max_rows):
        self.line_1 = line_1
        self.line_2 = line_2

        a = np.array([[self.line_1.a,self.line_1.b], [self.line_2.a,self.line_2.b]])
        b = np.array([self.line_1.rho, self.line_2.rho])

        x = np.linalg.solve(a, b)
        x_coord = x[0]
        y_coord = x[1]

        if x_coord < 0 or y_coord < 0 or x_coord >= max_cols or y_coord >= max_rows:
            raise Exception("Out of image")

        self.intersection = (x_coord, y_coord)


def main():
    img = cv2.imread('C:\\TFM\\imagenes\\finalRioWS-35880-897.jpeg')
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, thresh3 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    cv2.imwrite("C:\\TFM\\ws1\\zxcçty,.ç"
                "\\threshold.jpg", thresh3, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    edges = cv2.Canny(thresh3, 100, 200, apertureSize=3)
    # cv2.imwrite("C:\\TFM\\ws1\\test_final_alg\\canny.jpg", edges, [int(cv2.IMWRITE_JPEG_QUALITY), 100])


    """
    line ecuation: y = m*x +n
    polar:

        punto(3,6): indica que estamos a una distancia de 3 desde el origen de coordenadas con un angulo de 6

        p = x * cos(o) + y* sin(o)
        p =

    """

    lines = cv2.HoughLines(thresh3, 1, np.pi / 180, 400)
    line_equations = []
    shape = img.shape
    img_rows = shape[0]
    img_cols = shape[1]

    for line in lines:
        for rho, theta in line:
            a = np.cos(theta)
            b = np.sin(theta)
            #line_equations.append([[a, b], rho])
            line_equations.append(Line(a,b,rho))

    # calculate intersection for all lines
    # se puede hacer también con dos bucles for.
    combinations = itertools.combinations(line_equations, 2)
    intersections = []
    for combination in combinations:

        try:
            intersections.append(LineIntersection(combination[0],combination[1],img_cols,img_rows))
        except:
            # parallel lines or out of image.
            pass



    #### HOMOGRAPHY


    homography_candidates_ini = itertools.combinations(intersections, 4)
    homography_candidates_filter = []
    sum = 0
    area_threshold = 150000

    print(time.asctime(time.localtime(time.time())))
    for candidates_set in homography_candidates_ini:
        sum +=1
        if sum % 100000 ==0:
            print(sum)


        intersections_line_set = set()
        for intersecion in candidates_set:
            intersections_line_set.add(intersecion.line_1)
            intersections_line_set.add(intersecion.line_2)

        #print(len(intersections_line_set))
        if len(intersections_line_set)!=4:
            continue

        valid_candidate = True
        candidates_set_points = [candidates_set[0].intersection,candidates_set[1].intersection,candidates_set[2].intersection,candidates_set[3].intersection]
        triangles = itertools.combinations(candidates_set_points, 3)
        for triangle in triangles:
            area = triangle_area(triangle[0], triangle[1], triangle[2])
            if area < area_threshold:
                valid_candidate = False
                break
        if valid_candidate:
            homography_candidates_filter.append(candidates_set_points)


    print(time.asctime(time.localtime(time.time())))
    print(sum)
    print(len(homography_candidates_filter))

    # homography
    max_homography_ok_points = None
    best_homography_matrix = None
    c = BadmintonCourt()
    ground_truth_corners = c.court_external_4_corners()
    homography_checked = 0
    intersection_points = []
    for line_intersection in intersections:
        intersection_points.append(line_intersection.intersection)

    max_point_err_threshold = 3
    for homography_candidates in homography_candidates_filter:
        homography_checked += 1
        print(homography_checked)
        print(ground_truth_corners)
        print(homography_candidates)
        src_pts = np.array(ground_truth_corners, np.float32)
        dst_pts = np.array(homography_candidates, np.float32)
        # TODO ordenar puntos en el mismo orden.
        M, mask = cv2.findHomography(src_pts, dst_pts)
        pts = np.array(c.court_medium_corners(),np.float32).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, M)
        homography_ok_points = 0

        for dst_h in dst:
            min_dst = None
            for dst_r in intersection_points:
                d = euqlidean_distance(dst_h,dst_r)
                if min_dst == None or d < min_dst:
                    min_dst = d
                if min_dst <= max_point_err_threshold:
                    homography_ok_points +=1

        print_court_polylines(M, str(homography_checked))

        if max_homography_ok_points == None or homography_ok_points > max_homography_ok_points:
            print(homography_ok_points)
            max_homography_ok_points = homography_ok_points
            best_homography_matrix = M


    print(time.asctime(time.localtime(time.time())))

    print_court_polylines(best_homography_matrix, "final")
    print("matrix H: {}".format(best_homography_matrix))


def print_court_polylines(best_homography_matrix,sufix):
    #h = 1340
    #w = 610
    img = cv2.imread('C:\\TFM\\imagenes\\finalRioWS-35880-897.jpeg')
    for line in BadmintonCourt.court_lines():
        pts = np.float32([line]).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, best_homography_matrix)
        cv2.line(img, (dst[0][0][0],dst[0][0][1]), (dst[1][0][0],dst[1][0][1]), 255, 3)
        #img2 = cv2.polylines(img, [np.int32(dst)], True, 255, 3, cv2.LINE_AA)

    cv2.imwrite("C:\\TFM\\ws1\\test_final_alg\\results\\final_court_finder_lines{}.jpg".format(sufix), img,
                [int(cv2.IMWRITE_JPEG_QUALITY), 100])


if __name__ == "__main__":
    main()
