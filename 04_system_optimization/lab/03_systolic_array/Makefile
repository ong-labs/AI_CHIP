SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# week3 의 mac_prod.v 를 그대로 재사용
MAC_PROD := $(abspath $(CURDIR)/../../../04_system_optimization/lab/02_prod_mac/mac_prod.v)

# 모듈 reuse 시 mac_prod 의 $dumpfile 충돌 방지
COMPILE_ARGS += -DNO_VCD_DUMP

# 어떤 모듈을 테스트할지 결정 (default: pe_array)
TARGET ?= pe_array

ifeq ($(TARGET), pe_array)
    VERILOG_SOURCES := $(MAC_PROD) $(CURDIR)/pe_array.v
    TOPLEVEL := pe_array
    MODULE := test_pe_array
    # mac_prod 의 $dumpfile 충돌 피하고 pe_array 만 dump
    COMPILE_ARGS := -DNO_VCD_DUMP -DDUMP_PE_ARRAY
endif

ifeq ($(TARGET), input_skew)
    VERILOG_SOURCES := $(CURDIR)/input_skew.v
    TOPLEVEL := input_skew
    MODULE := test_input_skew
    COMPILE_ARGS :=
endif

ifeq ($(TARGET), weight_loader)
    VERILOG_SOURCES := $(CURDIR)/weight_loader.v
    TOPLEVEL := weight_loader
    MODULE := test_weight_loader
    COMPILE_ARGS :=
endif

ifeq ($(TARGET), output_collect)
    VERILOG_SOURCES := $(CURDIR)/output_collect.v
    TOPLEVEL := output_collect
    MODULE := test_output_collect
    COMPILE_ARGS :=
endif

ifeq ($(TARGET), systolic_top)
    VERILOG_SOURCES := $(MAC_PROD) \
                       $(CURDIR)/pe_array.v \
                       $(CURDIR)/input_skew.v \
                       $(CURDIR)/weight_loader.v \
                       $(CURDIR)/output_collect.v \
                       $(CURDIR)/systolic_top.v
    TOPLEVEL := systolic_top
    MODULE := test_systolic_top
    # sub-module 의 $dumpfile 충돌 피하고 systolic_top 만 dump
    COMPILE_ARGS := -DNO_VCD_DUMP -DDUMP_SYSTOLIC_TOP
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

# 모든 모듈 순차 실행: ./run_all.sh 또는 셸에서 for 루프 사용
.PHONY: clean-all
clean-all:
	rm -rf sim_build results.xml dump.vcd