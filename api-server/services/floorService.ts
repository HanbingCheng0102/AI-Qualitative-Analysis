import FloorRepository from "../repositories/floorRepository.ts";

type FloorPayload = {
  floor: {
    f2c: any[];
    a2c: any[];
  };
  name: string;
};

function isFloorPayload(value: any): value is FloorPayload {
  return (
    value &&
    typeof value === "object" &&
    typeof value.name === "string" &&
    value.floor &&
    Array.isArray(value.floor.f2c) &&
    Array.isArray(value.floor.a2c)
  );
}

class FloorService {
  constructor(private readonly repository: FloorRepository) {}

  async findAll() {
    return this.repository.findAll();
  }

  async create(payload: unknown) {
    if (!isFloorPayload(payload)) {
      throw new Error("Invalid floor payload.");
    }

    return this.repository.create(payload);
  }

  async update(id: string, payload: unknown) {
    if (!isFloorPayload(payload)) {
      throw new Error("Invalid floor payload.");
    }

    return this.repository.update(id, payload);
  }
}

export default FloorService;
