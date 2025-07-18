openapi: 3.0.3
info:
  title: Part Location Lookup Tool
  version: 1.0.0
  description: >
    Extracts part names and their corresponding physical location codes
    from text content such as system maintenance manuals or server PDFs.

servers:
  - url: https://<your-render-subdomain>.onrender.com

paths:
  /find-parts:
    post:
      summary: Extract part names and physical location codes
      operationId: findParts
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                text:
                  type: string
                  description: Text content from the PDF document
              required:
                - text
      responses:
        '200':
          description: List of part name and location code pairs
          content:
            application/json:
              schema:
                type: object
                properties:
                  original_text:
                    type: string
                  parts:
                    type: array
                    items:
                      type: object
                      properties:
                        part_name:
                          type: string
                        location_code:
                          type: string
