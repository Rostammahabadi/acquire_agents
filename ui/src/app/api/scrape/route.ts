import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);

export async function POST(request: Request) {
  try {
    // Path to the Python scraping script
    const scriptPath = path.join(process.cwd(), "..", "scrape_listings.py");

    // Run the Python scraping script
    const { stdout, stderr } = await execAsync(`python3 ${scriptPath}`, {
      cwd: path.join(process.cwd(), ".."),
      env: {
        ...process.env,
        PYTHONPATH: path.join(process.cwd(), ".."),
      },
    });

    if (stderr) {
      console.warn("Python script stderr:", stderr);
    }

    // Parse the JSON output from the Python script
    const result = JSON.parse(stdout.trim());

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error scraping listings:", error);

    // Try to extract more detailed error information
    let errorMessage = "Unknown error";
    let errorDetails = "";

    if (error instanceof Error) {
      errorMessage = error.message;
      if ("stderr" in error && error.stderr) {
        errorDetails = error.stderr.toString();
      }
    }

    return NextResponse.json(
      {
        error: "Failed to scrape listings",
        details: errorMessage,
        stderr: errorDetails,
      },
      { status: 500 }
    );
  }
}
