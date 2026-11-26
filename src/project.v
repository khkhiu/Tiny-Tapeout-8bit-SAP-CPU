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

  // TinyVGA PMOD
  assign uo_out = {hsync, B[0], G[0], R[0], vsync, B[1], G[1], R[1]};

  // Unused outputs assigned to 0.
  assign uio_out = 0;
  assign uio_oe  = 0;

  // Suppress unused signals warning
  wire _unused_ok = &{ena, ui_in, uio_in};

  reg [9:0] counter;

  hvsync_generator hvsync_gen(
    .clk(clk),
    .reset(~rst_n),
    .hsync(hsync),
    .vsync(vsync),
    .display_on(video_active),
    .hpos(pix_x),
    .vpos(pix_y)
  );
  
  wire [9:0] moving_x = pix_x * counter;

  assign R = video_active ? {moving_x[5], pix_y[2]} : 2'b00;
  assign G = video_active ? {moving_x[6], pix_y[2]} : 2'b00;
  assign B = video_active ? {moving_x[7], pix_y[5]} : 2'b00;
  
  always @(posedge vsync, negedge rst_n) begin
    if (~rst_n) begin
      counter <= 0;
    end else begin
      counter <= counter + 1;
    end
  end

  // Suppress unused signals warning
  wire _unused_ok_ = &{moving_x, pix_y};

endmodule
