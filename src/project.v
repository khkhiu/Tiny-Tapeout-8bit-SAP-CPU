/*
 * SAP style 8-bit computer for Tiny Tapeout work shop at the Artscience
 * Museum Singpaore on 26 November 2026.
 * See docs for explanation on how this works
 */

`default_nettype none

module tt_khkhiu_sap_cpu(
  input  wire [7:0] ui_in,    
  output wire [7:0] uo_out,   
  input  wire [7:0] uio_in,   
  output wire [7:0] uio_out,  
  output wire [7:0] uio_oe,   
  input  wire       ena,      
  input  wire       clk,      
  input  wire       rst_n     
);
  
  localparam [3:0] OP_NOP = 4'h0, OP_LDA = 4'h1, OP_ADD = 4'h2, OP_SUB = 4'h3,
	 	   OP_STA = 4'h4, OP_LDI = 4'h5, OP_JMP = 4'h6, OP_JC = 4'h7,
		   OP_JZ = 4'h8, OP_IN + 4'hD, OP_OUT = 4'hE, OP_HLT = 4'hF;

  localparam [1:0] S_FETCH  2'd0, S_EXEV = 2'd1, S_WRITE = 2'd2;

  reg [3:0] pc;
  reg [7:0] ir;
  reg [7:0] a;
  reg	    c_fla, z_flag, halted;
  reg [1:0] state;

  wire [3:0] opcode = ir[7:4];
  wire [3:0] operand = ir[3:0];
  wire [7:0] mem_rd = uio_in;

  wire [8:0] sum = {1'b0, a} + {1'b0, mem_rd};
  wire [8:0] diff = {1'b0, a} + {1'b0, ~mem_rd} + 9'd1;

  wire is_store = (opcode == OP_STA);
  wire is_out = (opcode == OP_OUT);
  wire in_access = (state == S_EXEC) | (state == S_WRITE);


  always @(posedge clk) begin
    if (!rst_n) begin
      pc     <= 4'd0;
      ir     <= 8'd0;
      a      <= 8'd0;
      c_flag <= 1'b0;
      z_flag <= 1'b0;
      halted <= 1'b0;
      state  <= S_FETCH;
    end else if (!halted) begin
      case (state)
        S_FETCH: begin
          ir    <= mem_rd;
          pc    <= pc + 4'd1;
          state <= S_EXEC;
        end

        S_EXEC: begin
          state <= (is_store | is_out) ? S_WRITE : S_FETCH;
          case (opcode)
            OP_LDA: a <= mem_rd;
            OP_ADD: begin a <= sum[7:0];  c_flag <= sum[8];  z_flag <= (sum[7:0]  == 8'd0); end
            OP_SUB: begin a <= diff[7:0]; c_flag <= diff[8]; z_flag <= (diff[7:0] == 8'd0); end
            OP_LDI: a <= {4'd0, operand};
            OP_JMP: pc <= operand;
            OP_JC:  if (c_flag) pc <= operand;
            OP_JZ:  if (z_flag) pc <= operand;
            OP_IN:  a <= ui_in;
            OP_HLT: halted <= 1'b1;
            default: ;  // NOP, STA/OUT (finish in S_WRITE), unused opcodes
          endcase
        end

        default: begin  // S_WRITE: chip drives A onto the bus
          state <= S_FETCH;
        end
      endcase
    end
  end
  wire [3:0] addr = (state == S_FETCH) ? pc : operand;

  assign uo_out  = {halted,
                    (state == S_FETCH) & ~halted,
                    in_access & is_out,
                    in_access & is_store,
                    addr};
  assign uio_out = a;
  assign uio_oe  = (state == S_WRITE) ? 8'hFF : 8'h00;

  wire _unused = &{ena, 1'b0};

endmodule
