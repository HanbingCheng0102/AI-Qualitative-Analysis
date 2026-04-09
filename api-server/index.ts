
import express from "express";

import { DriverFactory } from "./drivers/driverFactory.ts";
import StorageDriver from "./drivers/storageDriver.ts";

import env from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

// Walk up to find the root .env (shared with ai-service)
const __dirname = dirname(fileURLToPath(import.meta.url));
env.config({ path: resolve(__dirname, "../../.env") });
env.config(); // also load local .env if present, without overriding


async function main() {

    const app = express();
    app.use(express.json({ limit: "10mb" })); // increase the request size to allow for larger documents

    const uri = process.env.MONGO_URI;
    if (!uri) throw new Error("MONGO_URI is not set");

    console.log(`Connecting to MongoDB database ${uri}...`);


    // Create the storage driver
    const driver = DriverFactory.createDriver("mongo", {
        connectionString: uri
    });

    // Check that the connection worked
    if(!await driver.getDb()) 
        throw new Error("Failed to connect to the database. Please check your MONGO_URI and ensure the database is running.");


    // Set up CORS to allow requests from our React client
    app.use((req, res, next) => {
        res.header("Access-Control-Allow-Origin", "*"); // Allow all origins for simplicity
        res.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
        res.header("Access-Control-Allow-Headers", "Content-Type");
        if (req.method === "OPTIONS") {
            return res.sendStatus(200); // Handle preflight requests
        }
        next();
    });


    // Log all requests to console
    app.use((req, res, next) => {
        console.log(`Received request: ${req.method} ${req.path}`);
        const body = JSON.stringify(req.body, null, 2);
        console.log(body.split('\n').map(line => '  ' + line).join('\n'));
        next();
    });



    // Create a wrapper for each method in the driver to be called via RPC
    type AnyFn = (...args: any[]) => any;
    const dynamicDriver = driver as unknown as Record<string, AnyFn>;
    const handlers: Record<string, (...args: any[]) => Promise<any>> = {};

    for (const methodName of Object.getOwnPropertyNames(Object.getPrototypeOf(driver))) {
        const fn = dynamicDriver[methodName];
        if (methodName !== "constructor" && typeof fn === "function") {
            handlers[methodName] = async (...args: any[]) => {
                return await fn.apply(driver, args); // preserves `this`
            };
        }
    }



    // Expose the RPC endpoint, which takes a method name and parameters, calls the corresponding handler, and returns the result
    app.post("/rpc", async (req, res) => {

        // TODO: Authentication :)

        const { method, args } = req.body;

        if (!(method in handlers)) {
            return res.status(400).json({ error: "Unknown method" });
        }

        const out = await handlers[method](...args);
        res.json({ result: out });
    });

    const PORT = process.env.PORT || 3000;

    console.log(`Starting API server on port ${PORT}...`);
    app.listen(PORT);

};

main();