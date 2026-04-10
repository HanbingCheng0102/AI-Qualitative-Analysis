import { Db, ObjectId } from "mongodb";

type FloorRecord = {
  _id?: ObjectId | string;
  floor: {
    f2c: any[];
    a2c: any[];
  };
  name: string;
  updatedAt?: string;
};

class FloorRepository {
  constructor(private readonly getDb: () => Promise<Db>) {}

  private normalizeId(id: string) {
    return new ObjectId(id);
  }

  async findAll() {
    const db = await this.getDb();
    return db.collection("virtualFloors").find({}).toArray();
  }

  async create(floor: FloorRecord) {
    const db = await this.getDb();
    const payload = {
      ...floor,
      updatedAt: new Date().toISOString(),
    };
    const result = await db.collection("virtualFloors").insertOne(payload);
    return {
      _id: result.insertedId.toString(),
      ...payload,
    };
  }

  async update(id: string, floor: FloorRecord) {
    const db = await this.getDb();
    const payload = {
      ...floor,
      updatedAt: new Date().toISOString(),
    };

    await db.collection("virtualFloors").updateOne(
      { _id: this.normalizeId(id) },
      { $set: payload }
    );

    const saved = await db
      .collection("virtualFloors")
      .findOne({ _id: this.normalizeId(id) });

    if (!saved) {
      throw new Error("Failed to load floor after save.");
    }

    return saved;
  }
}

export default FloorRepository;
