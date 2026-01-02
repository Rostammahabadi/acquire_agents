import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("job_id");

    if (!jobId) {
      return NextResponse.json(
        { success: false, message: "job_id parameter is required" },
        { status: 400 }
      );
    }

    // Call the FastAPI server to check job status
    const fastApiResponse = await fetch(
      `http://localhost:8000/api/run/deep-research/status/${jobId}`,
      {
        method: "GET",
        headers: {
          Authorization: "Bearer demo-token", // Use demo token for now
        },
      }
    );

    if (!fastApiResponse.ok) {
      const errorData = await fastApiResponse.json();
      throw new Error(errorData.detail || "Failed to get job status");
    }

    const statusResult = await fastApiResponse.json();

    return NextResponse.json({
      success: true,
      job_id: statusResult.job_id,
      status: statusResult.status,
      results: statusResult.results,
      error: statusResult.error,
      completed_at: statusResult.completed_at,
    });
  } catch (error) {
    console.error("Deep research status error:", error);
    return NextResponse.json(
      {
        success: false,
        message:
          error instanceof Error ? error.message : "Unknown error occurred",
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const { business_id, sector_description } = await request.json();

    if (!sector_description) {
      return NextResponse.json(
        { success: false, message: "sector_description is required" },
        { status: 400 }
      );
    }

    // Call the FastAPI server to start deep research (runs in background)
    const fastApiResponse = await fetch(
      "http://localhost:8000/api/run/deep-research",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer demo-token", // Use demo token for now
        },
        body: JSON.stringify({
          business_id,
          sector_description,
        }),
      }
    );

    if (!fastApiResponse.ok) {
      const errorData = await fastApiResponse.json();
      throw new Error(errorData.detail || "FastAPI request failed");
    }

    const fastApiResult = await fastApiResponse.json();

    // Return the job ID immediately - frontend will poll for status
    return NextResponse.json({
      success: true,
      job_id: fastApiResult.run_id,
      message: "Deep research started - results will be available shortly",
      status: "running",
    });
  } catch (error) {
    console.error("Deep research error:", error);
    return NextResponse.json(
      {
        success: false,
        message:
          error instanceof Error ? error.message : "Unknown error occurred",
      },
      { status: 500 }
    );
  }
}
