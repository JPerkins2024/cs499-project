# DSI File Format 
The DSI format is yaml based with some keywords defined for ease of use.
The basic format of a dsi file is a yaml document containing toplevel dictionaries describing a simulation unit.
A verbose example can be found below.  The control block under default is merged into all other parameters.

```
default:
  control:
    corners: nom
    models path: /home/difcm/MDL_AUC/c11hv/model_wa/wellsjeremy/titan/models/include.tit
    simulator: titan
R7057_ZA105354_03_HVN16P_ls_dc1_mgd_id_vd_vg_0:
  instance parameters:
    w: 9.999999999999999e-06
    l: 3e-07
    nx: 2.0
  stimuli:
    vd:
      start: -0.2
      stop: 18.0
      step: 0.1
      type: lin
    vg:
      start: 0.0
      stop: 3.6
      step: 0.4
      type: lin
    vb: 0.0
  control:
    temperature: -20.0
  sweep:
    1: vd
    2: vg
  definitions:
    device_type: nmos
    analysis_type: idsweep
  device: hvn16p_lsc11hv
  views:
    R7057_ZA105354_03_HVN16P_ls_dc1_mgd_id_vd_vg_0:
      type: texgraph
      config:
        title: hvn16p_lsc11hv id-vd w = 1e-05 l = 3e-07 nx = 2
        xlabel: VD
        ylabel: ID
        corner_specific:
          measure:
            only marks: true
            thin: true
            mark: o
            mark size: 1pt
          default:
            no markers: true
            thin: true
            solid: true
  simulations:
    measure:
      sweep:
      - - '-0.2'
        - 
        - -1.0338e-10
      - - '-0.1'
        - 
        - -1.7e-12
      - - '0'
        - 
        - -4e-13
      - - '0.1'
        - 
        - -3.2e-13
      - - '0.2'
        - 
        - -4.6e-13
```
Below a description of the various components can be found.
## Definitions
The definitions block has two functions.  It acts a store for arbitrary variables that are not directly used in simulation, but may be used as inputs to analyses (any required definition that is not defined will throw an error asking for a definition).  Common definitions are Vdd, Vgg, Vdlin, which can be used to parameterize metrics across devices.  Devsim also uses keywords that are placed in definitions.  Some of these values have defaults that exist in devsim's config directory, but can also be defined in either a techfile or a dsi file.  The config has the lowest priority for all configuration, then the techfile, and the dsi file has the highest.
Keyword definitions are as follows:

|Param         | Description                                                                                                                                                                            |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| device_type  | describes the device.  Example: "nmos","pmos", "nmos4t","nmos5t","diode".  An exhaustive list can be found in the default [configuration](./src/conf/config.yml)                       |
|analysis_type | Metric analysis to perform.  This maps to functions defined in [measures.py](./src/ifxdevsim/measures.py)  Generic measures are also accepted (i\<port\>,v\<port\>, cgd,cgs,cgg, etc.) |
| model        | model name.  If device is specified this is not needed.                                                                                                                                |
|reverse sweep | invert some definitions for P-type devices (true|false)|
| instance             | Letter used to instantiate device.  Usually one of 'x','m','d','r','q'.  If using device_type, not needed to specify explicitly                                               |
| ports             | Space delimited list of ports|
| vmin             | min value to use in sweep measurements for a device                                                                                                                                                                                       |
| vmax             | maximum value to use in sweep measurements for a device                                                                                                                                                                                      |
| frequency             | frequency to use in AC measures                                                                                                                                                                                      |
| itar             | Target current for constant current measures (like vtc)                                                                                                                                                                                       |
| \_no\_instance\_params                 | Do not netlist instance params.  Used if using a layout extracted netlist.                                                                                                                                                                                                                                              |
|     units                                 | units to convert raw results into.  Si conversion is supported.                                                                                                                                                                                                                                                                                                                        |
| scale\_w\_perim                                          | equation for defining width used in unit conversion (e.g ua/um)                                                                                                                                                                                                                                                                                                                                                                                       |
| scale\_area                                          | equation for defining area for unit conversion                                                                                                                                                                                                                                                                                                                                                                                       |
| square                                          | equation for defining square (sq) for unit conversion                                                                                                                                                                                                                                                                                                                                                                                       |

## Stimuli
Stimuli define how to bias a device.  A number, a parameter defined in definitions, or a sweep dictionary are supported.
Linear, logarithmic, and list sweeps are supported.  Using the dictionary format can improve simulation times as a more efficient measurement scheme is used in linear sweep cases.
Examples below:
```
stimuli:
    vd_lin1:
      start: -0.2
      stop: 18.0
      step: 0.1
      type: lin
    vd_lin2:
      start: -0.2
      stop: 18.0
      num steps: 100
      type: lin
    vd_lin2:
      start: -0.2
      stop: 18.0
      num steps: 100
      type: lin
    vd_log:
        type: log
        start: -0.2 #value
        stop: 18 #value
        step: 10 #steps/dec.
    vd_list:
        type: list
        list: 
        - 1
        - 2
        - 3
        ...
```


## Sweep
Defines sweep order.  Only valid keys are 1 and 2, for first and second order.  Expects a string that appears in either stimuli or instance parameters.
This is optional, and only needed if generating sweep/vector data.


## Metrics
Metrics are defined in the techfile.  They are "superset" parameters that have merge metric specific configurations into other fields.
Example from a c11hv techfile (definitions and stimuli would be merged here):
```
  vtlin_ldmos:
  #valid_types used to assign metric to ModelInfo devices types
    type: metric
    definitions:
      analysis_type: vtc
      itar: icrit*w*mult_factor/l
    stimuli:
      vd: vdlin
      vg: vgg
    plot:
    - x: w
      title: '@device@ @metric@ W trend @params@'
      params:
      - temperature
      - vd
      - nx
    - x: nx
      title: '@device@ @metric@ NX trend @params@'
      params:
      - temperature
      - vd
      - w
    measure:
      curve:
        y: id
        x: vg
      routine:
        name: calc_vtc
        args:
        - itar
      stimuli:
        vd: vdlin
        vb: 0
```

## Simulation
Dictionary that has previously simulated values.  This will either be overwritten by new sims or merged, if a measurement is defined here.

## Control
Contains simulation control statements that would make a parameter incompatible with others, and would require a separate simulation deck.
A non-exhaustive list of configuration options is below:


|Param          | Description                                                                               |
| ------------- | ----------------------------------------------------------------------------------------- |
| temperature   | temperature                                                                               |
| mode          | one of normal or montecarlo or tmi/omi aging (TODO)                                       |
|step size      | step size for global sweep                                                                |
| simulator     | simulator                                                                                 |
| tprint        | transient sim option for transient metrics                                                |
| tstop         | transient sim option for transient metrics                                                |
| load balancer | string to use for launching jobs.  Usually do not need to adjust this.                    |
| montecarlo    | dictionary: {args: string to append to montecarlo statement, syntax: simulator language}  |
| tran          | transient sim pass through, will write exactly what is said here.  Usually used for aging |
|models path    | path to models.  Can be semicolon delimited                                               |
| corners       | corners to include.  Either defined in techfile directly or written in regression corner style syntax.                                                                                          |
### Corner syntax
To specify multiple corners, set the control: corners section to be a colon delimited list of comma delimited modular corners.
A complex example is below.  If specifying this style in the techfile, use semicolons(;) instead of commas.
```
mos_mc,mos_tt,mos_ff,mos_ss,mos_fs,mos_sf,mos_ttg,mos_ffg,mos_ssg,mos_fsg,mos_sfg,mos_flvshv,mos_slvfhv,mos_flvshvg,mos_slvfhvg:dio_mc,dio_tt,dio_ff,dio_ss:bjt_mc,bjt_tt,bjt_ff,bjt_ss:res_tt,res_ff,res_ss:var_mc,var_tt,var_ff,var_ss:cell_program_tt,cell_erase_tt,cell_uv_tt:pip_tt,pip_ss,pip_ff:cap_tt,cap_ss,cap_ff:mom_mc,mom_tt,mom_ss,mom_ff
```
The rules for this syntax are that the first colon delimited field must have the most number of corners being varied.  Each modular corner will be iterated with the first corner until the end of that respective corner's list, and
then the first corner specified will be used afterwards.
## Instance Parameters
These values are passed through to the instance line of the device.  Not much else is done here.  These are often referenced in equations defined in definitions.

# Generate DSI files from measurements
Two types of DSI files can be generated from raw measurement data.  Full I-V sweeps and post-processed metrics are the two types currently supported.
Devsim supports reading files of the mdm, mea, and proplusdat filetypes, all python packages developed by Infineon.
Additionally, a measurement replay file and mapping file are generated to preserve what was done.
Running `dvsim -m <path to meas directory> -md` will generate a `devsim_device_map.yml` and a measurement replay file that contains a list of measurements used as an input.
The replay file can be edited to filter out unwanted curves and generate a smaller dsi file using the `-mf` and `-mdsi/mkop` arguments.

An example device map can be found below. Datfile and mea configuration are similar.  Use fileglobs to match filenames and define device type and model names. Optionally, scale can be used to scale specific parameters by the factor specified.
Similarly, default is merged into all for a category.
MDM files use a different scheme, since more information is available in the file.  We assume it is a waferpro express output 
and the routine name and polarity are used.  It is likely that this will be refactored to be similar to dat and mea at some point if this is insufficient for uniqueness.
```
mdm:
  ai22_mosfet_n:
    device_type: nmos4t
    model: n_shv5v
  default: {}
dat:
  default: {}
  LD3P3TN1P8_DNW_*.dat:
    device_type: nmos4t
    model: ld3p3tn1p8_dnw
  nshort*.dat:
    device_type: nmos4t
    model: nshort
  ndiode*.dat:
    device_type: diode2t
    model: ndiode
    scale:
      area: 1e12
      pj: 1e6
mea:
  default: 
    scale: 
      w: 1e-6 
      l: 1e-6 
  R7057_ZA105354_03_HVN16P*.mea:
    device_type: nmos
    model: hvn16p_lsc11hv
```
This mapfile is used to help write dsi files from measurements.

Once a dsi file is written from measurements, a user may need to add models path and corners to the default control statement before it is simulatable.
## Configuring techfile metrics for DSI generation/Measurement post-processing
When devsim reads a measurement file, and a techfile is defined, it will check the metrics to see if any for a device are supported for a given sweep.
The measure section defines configuration for postprocessing routines for a sweep as well as which routine /arguments should be used to post-process the measurement from a dataset of x/y values.
Each portion below has a commented explanation.
```
    measure:
    # Curve: filter sweeps based on x node and y output.
      curve:
        y: id
        x: vg
    # Post-processing routine to use.  Use -print-metric-routines to get a list of available post-processing routines.
      routine:
        name: calc_vtc
        args:
        - itar
    # Bias filter, so that the correct sweep is used once the curve matches.
      stimuli:
        vd: vdlin
        vb: 0
```
Plot configuration is also generatable and parameterizible when generating KOP metrics.  Multiple plot configurations can be defined for the same metric.
The three "@" surrounded variables below are parameterized for easy portability.
The p: key allows for a secondary variable.  Corners are by default always plotted.
The params field will generate a unique view name for each device to prevent too much data appearing in a single graph.
If you see too much data in a plot, it is likely that more parameters need to be added for uniquification, or a secondary sweep is needed.
```
    plot:
    - x: w
      title: '@device@ @metric@ W trend @params@'
      params:
      - temperature
      - vd
      - nx
    - x: w
      title: '@device@ @metric@ W trend @params@'
      params:
      - temperature
      - vd
      p: nx
    - x: nx
      title: '@device@ @metric@ NX trend @params@'
      params:
      - temperature
      - vd
      - w
```

