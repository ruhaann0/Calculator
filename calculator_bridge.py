from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os

FOLDER = os.path.dirname(os.path.abspath(__file__))

VERILOG_CODE = """
module calculator(
    input [3:0] A,
    input [3:0] B,
    input [1:0] operation,
    output reg [7:0] result,
    output reg error
);
always @(*) begin
    result = 0;
    error = 0;
    case (operation)
        2'b00: result = A + B;
        2'b01: result = A - B;
        2'b10: result = A * B;
        2'b11: begin
            if (B != 0)
                result = A / B;
            else
                error = 1;
        end
    endcase
end
endmodule
"""

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def do_POST(self):
        if self.path != "/calculate":
            self.send_error(404)
            return

        try:
            length = int(self.headers["Content-Length"])
            data = json.loads(self.rfile.read(length))

            a = int(data["a"])
            b = int(data["b"])
            op = data["op"]

            if not (0 <= a <= 15 and 0 <= b <= 15):
                raise ValueError("Use numbers from 0 to 15.")

            operations = {
                "+": "00",
                "-": "01",
                "*": "10",
                "/": "11"
            }

            if op not in operations:
                raise ValueError("Invalid operation.")

            tb = f"""
module tb;
reg [3:0] A, B;
reg [1:0] operation;
wire [7:0] result;
wire error;

calculator uut(A, B, operation, result, error);

initial begin
    A = 4'd{a};
    B = 4'd{b};
    operation = 2'b{operations[op]};
    #1;
    if (error)
        $display("ERROR");
    else
        $display("RESULT=%0d", result);
    $finish;
end
endmodule
"""

            with open(os.path.join(FOLDER, "calculator.v"), "w") as f:
                f.write(VERILOG_CODE)

            with open(os.path.join(FOLDER, "calculator_tb.v"), "w") as f:
                f.write(tb)

            subprocess.run(
                ["iverilog", "-o", "calculator_sim",
                 "calculator.v", "calculator_tb.v"],
                cwd=FOLDER, check=True, capture_output=True, text=True
            )

            run = subprocess.run(
                ["vvp", "calculator_sim"],
                cwd=FOLDER, check=True, capture_output=True, text=True
            )

            output = run.stdout.strip()
            result = {"result": output.split("=", 1)[1]} if output.startswith("RESULT=") else {"error": output}

            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            body = json.dumps({"error": str(e)}).encode()
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *args):
        pass

server = HTTPServer(("127.0.0.1", 8000), Handler)
print("Verilog calculator bridge running at http://127.0.0.1:8000")
server.serve_forever()