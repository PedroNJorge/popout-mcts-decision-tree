class Block:
    def __init__(self, x, y):
        # x1 <= x2 & y1 <= y2, always
        self.x1 = self.x2 = x
        self.y1 = self.y2 = y
        self.orientation = "upright"    # "upright", "vertical", "horizontal"
        self.move_counter = 0

    def __str__(self):
        return f"(({self.x1}, {self.y1}),({self.x2}, {self.y2})): {self.orientation}"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (
                isinstance(other, Block)
                and self.x1 == other.x1
                and self.x2 == other.x2
                and self.y1 == other.y1
                and self.y2 == other.y2
                and self.orientation == other.orientation
        )

    def __hash__(self):
        return hash((self.x1, self.y1, self.x2, self.y2, self.orientation))

    def move(self, direction):
        self.move_counter += 1
        match self.orientation:
            case "upright":
                match direction:
                    case "up":
                        self.x1 -= 2
                        self.x2 -= 1
                    case "down":
                        self.x1 += 1
                        self.x2 += 2
                    case "left":
                        self.y1 -= 2
                        self.y2 -= 1
                    case "right":
                        self.y1 += 1
                        self.y2 += 2

            case "vertical":
                match direction:
                    case "up":
                        self.x1 = self.x2 = min(self.x1, self.x2) - 1
                    case "down":
                        self.x1 = self.x2 = max(self.x1, self.x2) + 1
                    case "left":
                        self.y1 -= 1
                        self.y2 -= 1
                    case "right":
                        self.y1 += 1
                        self.y2 += 1

            case "horizontal":
                match direction:
                    case "up":
                        self.x1 -= 1
                        self.x2 -= 1
                    case "down":
                        self.x1 += 1
                        self.x2 += 1
                    case "left":
                        self.y1 = self.y2 = min(self.y1, self.y2) - 1
                    case "right":
                        self.y1 = self.y2 = max(self.y1, self.y2) + 1

        self.update_orientation(direction)

    def update_orientation(self, direction):
        match(self.orientation):
            case "upright":
                match(direction):
                    case "up" | "down":
                        self.orientation = "vertical"

                    case "left" | "right":
                        self.orientation = "horizontal"

            case "vertical":
                match(direction):
                    case "up" | "down":
                        self.orientation = "upright"

            case "horizontal":
                match(direction):
                    case "left" | "right":
                        self.orientation = "upright"
