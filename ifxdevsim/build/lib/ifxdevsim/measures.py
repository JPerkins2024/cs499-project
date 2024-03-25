import re
import numpy as np
from copy import deepcopy
from .utils import expand_generic_sweep
from .flatten import flatten

class MeasureError(Exception):
    pass 


class MeasuresMixin:
    def vt(self, ports,k):
        
        required_ports = ['d', 'g', 's']
        self.check_prereqs(ports, required_ports)
        self.unit = "v"
        self.type = "sweep"
        sweep_str, txt, mult = self.get_sweep_supply(k)
        str = []
        str.append(self.get_instance_line(k,ports))
        str.append(sweep_str)
        ports.remove('g')
        str.append(self.get_stimuli(k,ports,[]))
        
        simulator = self.param_data['control']['simulator']
        if simulator == "spectre" or "aps" or "xps":
            
            str.append(".measure dc gm_{k} deriv i(vd_{k})".format(k  = k))
            str.append(".measure dc max_gm_{k} {txt} gm_{k}".format(k = k, txt = txt))
            str.append(".measure dc v_max_gm_{k} when gm_{k}=max_gm_{k}".format(k = k))
            str.append(".measure dc i_max_gm_{k} find i(vd_{k}) when v(v_master)=v_max_gm_{k}".format(k = k))
            str.append(".measure dc vd_{k} find v(d_{k}) when v(v_master)=v_max_gm_{k}".format(k = k))
            str.append(".measure dc vs_{k} find v(s_{k}) when v(v_master)=v_max_gm_{k}".format(k = k))
            str.append(".measure dc {find_measure_name} param='{mult}v_max_gm_{k}-{mult}i_max_gm_{k}/max_gm_{k}-vs_{k}-(vd_{k}-vs_{k})/2.0'".format(k = k, mult = mult, find_measure_name = self.find_measure_name(k)))
        elif simulator == "eldo" or "premier":
            str.append(".defwave dc gm_{k}=deriv(i(vd_{k}))".format(k))
            str.append(".measure dc max_gm_{k} {txt} w(gm_{k})".format(k))
            str.append(".measure dc v_max_gm_{k} when w(gm_{k})=max_gm_{k}".format(k))
            str.append(".measure dc i_max_gm_{k} find i(vd_{k}) when v(v_master)=v_max_gm_{k}".format(k))
            str.append(".measure dc vd_{k} find v(d_{k}) when v(v_master)=v_max_gm_{k}".format(k))
            str.append(".measure dc vs_{k} find v(s_{k}) when v(v_master)=v_max_gm_{k}".format(k))
            str.append(".measure dc {find_measure_name} param='{mult}v_max_gm_{k}-{mult}i_max_gm_{k}/max_gm_{k}-vs_{k}-(vd_{k}-vs_{k})/2.0'".format(find_measure_name = self.find_measure_name(k), k = k, mult = mult))
        elif simulator == "hspice":
            str.append(".probe dc gm_{k}=deriv(\"i(vd_{k})\")".format(k = k))
            str.append(".measure dc max_gm_{k} {txt} par(gm_{k})".format(k = k, txt = txt))
            str.append(".measure dc v_max_gm_{k} when par(gm_{k})=max_gm_{k}".format(k = k))
            str.append(".measure dc i_max_gm_{k} find i(vd_{k}) when v(v_master)=v_max_gm_{k}".format(k = k))
            str.append(".measure dc vd_{k} find v(d_{k}) when v(v_master)=v_max_gm_{k}".format(k = k))
            str.append(".measure dc vs_{k} find v(s_{k}) when v(v_master)=v_max_gm_{k}".format(k = k))
            str.append(".measure dc {find_measure_name} param='{mult}v_max_gm_{k}-{mult}i_max_gm_{k}/max_gm_{k}-vs_{k}-(vd_{k}-vs_{k})/2.0'".format(find_measure_name = self.find_measure_name(k), k = k, mult = mult))
        elif simulator == "titan":
            str.append(".measure dc gm_{k} 'deriv(i(vd_{k}))'".format(k = k))
            str.append(".measure dc max_gm_{k} {txt} 'deriv(i(vd_{k}))'".format(k = k, txt = txt))
            str.append(".measure dc v_max_gm_{k} x{txt} 'deriv(i(vd_{k}))'".format(k = k, txt = txt))
            str.append(".measure dc i_max_gm_{k} e{txt} 'deriv(i(vd_{k}))' expr(xval)= 'i(vd_{k})'".format(k = k, txt = txt))
            str.append(".measure dc vd_{k} e{txt} 'deriv(i(vd_{k}))' expr(xval)= 'v(d_{k})'".format(k = k, txt = txt))
            str.append(".measure dc vs_{k} e{txt} 'deriv(i(vd_{k}))' expr(xval)= 'v(s_{k})'".format(k = k, txt = txt))
            str.append(".measure dc {find_measure_name} param='{mult}m(v_max_gm_{k})-{mult}m(i_max_gm_{k})/m(max_gm_{k})-m(vs_{k})-(m(vd_{k})-m(vs_{k}))/2.0'".format(find_measure_name = self.find_measure_name(k), k = k, mult = mult))
        else:
            return ""

        return "\n".join(str)

    def vtc(self, ports, k):
        
        required_ports = ['d', 'g', 's']
        itar = self.get_defs(['itar'])
        self.check_prereqs(ports, required_ports)
        self.unit = "v"
        self.type = "sweep"
        sweep_str, txt, mult = self.get_sweep_supply(k)
        vtcc_mode = self.get_defs(['vtcc_mode'], None)
        str = []
        str.append(self.get_instance_line(k,ports))
        str.append(sweep_str)
        ports.remove('g')
        str.append(self.get_stimuli(k,ports,[]))
        try: 
            if 1.1*10**-12 > abs((float(itar))):
                raise MeasureError("Invalid constant current {itar} for {find_measure_name}.".format(find_measure_name = self.find_measure_name(k), itar = itar))
        except ValueError:
            print(self.param_data)
            raise



        if vtcc_mode == "source":
            str.append(".measure dc vtc_{k} find v(g_{k}) when i(vs_{k}) = '{itar}'".format(k = k, itar = itar))
            str.append(".measure dc vsrc_{k} find v(s_{k}) when i(vs {k}) = '{itar}'".format(k = k, itar = itar))
        else:
            str.append(".measure dc vtc_{k} find v(g_{k}) when i(vd_{k}) = '-1*{itar}'".format(k = k, itar = itar))
            str.append(".measure dc vsrc_{k} find v(s_{k}) when i(vd_{k}) = '-1*{itar}'".format(k = k, itar = itar))
        str.append(".measure dc {find_measure_name} param='vtc_{k}-vsrc_{k}'".format(find_measure_name = self.find_measure_name(k), k = k))
        return ["\n".join(str), ["vtc_{k}".format(k = k), "vsrc_{k}".format(k = k)]]

    def gmmax(self, ports, k):
        
        required_ports = ['d', 'g', 's']
        self.check_prereqs(ports, required_ports)
        self.unit = "a/v"
        self.type = 'sweep'
        sweep_str, txt, mult = self.get_sweep_supply(k)
        str = []
        str.append(self.get_instance_line(k,ports))
        str.append(sweep_str)
        str.append(self.get_stimuli(k,ports-['g'],[]))

        simulator = self.param_data['control']['simulator']
        if simulator == "spectre" or "aps" or "xps":
            str.append(".measure dc gm_{k} deriv i(vd_{k})".format(k = k))
            str.append(".measure dc max_gm_{k} {txt} gm_{k}".format(k = k))
        elif simulator == "eldo" or "premier":
            str.append(".defwave dc gm_{k}=deriv(i(vd_{k}))".format(k = k))
            str.append(".measure dc max_gm_{k} {txt} w(gm_{k})".format(k = k, txt = txt))
        elif simulator == "hspice":
            str.append(".probe dc gm_{k}=deriv(\"i(vd_{k})\")".format(k = k))
            str.append(".measure dc max_gm_{k} {txt} par(gm_{k})".format(k = k, txt = txt))
        elif simulator == "titan":
            str.append(".measure dc max_gm_{k} {txt} 'deriv(i(vd_{k}))'".format(k = k, txt = txt))
        else:
            return ""
        str.append(".measure dc {find_measure_name} param='max_gm_{k}'".format(k = k, find_measure_name = self.find_measure_name(k)))
        return ["\n".join(str),["max_gm_{k}".format(k = k)]]

    def beta(self, ports, k):
        
        required_ports = ['c', 'b']
        self.check_prereqs(ports, required_ports)
        self.unit = None
        self.type = "dc"
        str = []
        str.append(self.get_instance_and_stimuli(k,ports,[]))
        str.append(".measure dc {find_measure_name} param='i(vc_{k})/i(vb_{k})'".format(k = k, find_measure_name = self.find_measure_name(k)))
        return "\n".join(str)

    def ibrat(self, ports, k):
        
        required_ports = ['d', 'g', 's']
        self.check_prereqs(ports, required_ports)
        self.unit = None
        self.type = "dc"
        str = []
        str.append(self.get_instance_and_stimuli(k,ports,[]))
        str.append(".measure dc {find_measure_name} param='-1*i(vb_{k})/i(vd_{k})'".format(k = k, find_measure_name = self.find_measure_name(k)))
        return "\n".join(str)

    def ibbrat(self, ports, k):
        
        required_ports = ['d', 'g', 's']
        self.check_prereqs(ports,required_ports)
        self.unit = 'v'
        self.type = 'sweep'
        sweep_str,txt,mult = self.get_sweep_supply(k)

        if txt == "max":
            ib_txt = "min"
        else:
            ib_txt = "max"
        
        str = []
        str.append(self.get_instance_line(k, ports))
        str.append(sweep_str)
        str.append(self.get_stimuli(k, ports-['g'],[]))
        str.append(".measure dc tempibb_{k} {ib_txt} i(vb_{k})".format(k = k, ib_txt = ib_txt))
        str.append(".measure dc tempidd_{k} find i(vd_{k}) when i(vb_{k}) = tempibb_{k}".format(k = k))
        str.append(".measure dc {find_measure_name} param='-1*tempibb_{k}/tempidd_{k}'".format(k = k, find_measure_name = self.find_measure_name(k)))
        return ["\n".join(str), ["tempibb_{k}".format(k), "tempidd_{k}".format(k)]]

    def ibb(self, ports, k):
        
        required_ports = ['g','b']
        self.check_prereqs(ports,required_ports)
        self.unit = 'a'
        self.type = 'sweep'
        sweep_str,txt,mult = self.get_sweep_supply(k)

        if txt == 'max':
            ib_txt = 'min'
        else:
            ib_txt = 'max'

        str = []
        str.append(self.get_instance_line(k,ports))
        str.append(sweep_str)
        str.append(self.get_stimuli(k,ports-['g'],[]))
        str.append(".measure dc tempibb_{k} {ib_txt} i(vb_{k})".format(k = k, ib_txt = ib_txt))
        str.append(".measure dc {find_measure_name} param='-1*tempibb_{k}'".format(k = k, find_measure_name = self.find_measure_name(k)))
        return ["\n".join(str),["tempibb_{k}".format(k = k)]]


    def vibb(self, ports, k):
        
        required_ports = ['g','b']
        self.check_prereqs(ports,required_ports)
        self.unit = 'v'
        self.type = "sweep"

        sweep_str, txt, mult = self.get_sweep_supply(k)

        if txt == 'max':
            ib_txt = 'min'
        else:
            ib_txt = 'max'
        
        str = []
        str.append(self.get_instance_line(k,ports))
        str.append(sweep_str)
        str.append(self.get_stimuli(k,ports-['g'],[]))
        str.append(".measure dc tempibb_{k} {ib_txt} i(vb_{k})".format(k = k, ib_txt = ib_txt))
        str.append(".measure dc tempvibb_{k} when i(vb_{k}) = tempibb_{k}".format(k = k))
        str.append(".measure dc {find_measure_name} param='tempvibb_{k}'".format(k = k, find_measure_name = self.find_measure_name(k)))

        return ["\n".join(str), ["tempibb_{k}".format(k),"tempvibb_{k}".format(k)]]

    def gm(self, ports, k):
        
        required_ports = ['g','d']
        self.check_prereqs(ports, required_ports)
        self.unit = 's'
        self.type = 'sweep'

        reverse_sweep = self.get_defs(['reverse sweep'])
        step_size = self.param_data['control']['step_size']
        vd = self.find_port_stimulus('d')
        target2 = float(self.param_data['stimuli']['vg'])

        if reverse_sweep:
            vsweep = 'n_master'
            target1 = target2 + step_size
        else:
            vsweep = 'v_master'
            target1 = target2 - step_size
        
        vmin = min(target1, target2)
        vmax = max(target1, target2)
        str = []
        str.append(self.get_instance_line(k,ports))
        str.append("eg_{k} g_{k} 0 vol='min({vmax},max({vmin},v({vsweep})))' ".format(k = k, vd = vd, vsweep = vsweep, vmin = vmin, vmax = vmax))
        str.append(self.get_stimuli(k,ports-['g'],[]))
        str.append(".measure dc temp_gm1_{k} find i({vd}_{k}) when v({vsweep})={target1}".format(k = k, vd = vd, vsweep = vsweep, target1 = target1))
        str.append(".measure dc temp_gm2_{k} find i({vd}_{k}) when v({vsweep})={target2}".format(k = k, vd = vd, vsweep = vsweep, target2 = target2))
        str.append(".measure dc {find_measure_name} param='(temp_gm1_{k}-temp_gm2_{k})/{step_size}'".format(k = k, find_measure_name = self.find_measure_name(k), step_size = step_size))

        return ["\n".join(str), ["temp_gm1_{k}".format(k=k), "temp_gm2_{k}".format(k=k)]]

    def gds(self, ports, k):
        
        required_ports = ['d']
        self.check_prereqs(ports, required_ports)
        self.unit = 's'
        self.type = 'sweep'
        reverse_sweep,step_size = self.get_defs(['reverse sweep'])
        step_size = self.param_data['control']['step size']
        target2 = float(self.param_data['stimuli']['vd'])

        if reverse_sweep:
            vsweep = 'n_master'
            target1 = target2 + step_size
        else:
            vsweep = 'v_master'
            target1 = target2 - step_size

        vmin = min(target1, target2)
        vmax = max(target1, target2)
        
        str = []
        str.append(self.get_instance_line(k,ports))
        str.append("ed_{k} d_{k} 0 vol='min({vmax},max({vmin},v({vsweep})))' ".format(k = k, vsweep = vsweep, vmin = vmin, vmax = vmax))
        str.append(self.get_stimuli(k,ports-['d'],[]))
        str.append(".measure dc temp_gds1_{k} find i(ed_{k}) when v({vsweep})={target1}".format(k = k, vsweep = vsweep, target1 = target1))
        str.append(".measure dc temp_gds2_{k} find i(ed_{k}) when v({vsweep})={target2}".format(k = k, vsweep = vsweep, target2 = target2))
        str.append(".measure dc {find_measure_name} param='(temp_gds1_{k}-temp_gds2_{k})/{step_size}'".format(k = k, find_measure_name = self.find_measure_name(k), step_size = step_size))

        return ["\n".join(str), ["temp_gds1_{k}", "temp_gds2_{k}"]]

    def ro(self, ports, k):
        
        required_ports = ['d']
        self.check_prereqs(ports, required_ports)
        self.unit = 's'
        self.type = 'sweep'

        reverse_sweep, step_size = self.get_defs(['reverse sweep'])
        step_size = self.param_data['control']['step size']
        target2 = float(self.param_data['stimuli']['vd'])
        if reverse_sweep:
            vsweep = 'n_master'
            target1 = target2 + step_size
        else:
            vsweep = 'v_master'
            target1 = target2 - step_size
        
        vmin = min(target1, target2)
        vmax = max(target1, target2)

        str = []
        str.append(self.get_instance_line(k,ports))
        str.append("ed_{k} d_{k} 0 vol='min({vmax},max({vmin},v({vsweep})))' ".format(k = k, vsweep = vsweep, vmin = vmin, vmax = vmax))
        str.append(self.get_stimuli(k,ports-['d'],[]))
        str.append(".measure dc temp_ro1_{k} find i(ed_{k}) when v({vsweep})={target1}".format(k = k, vsweep = vsweep, target1 = target1))
        str.append(".measure dc temp_ro2_{k} find i(ed_{k}) when v({vsweep})={target2}".format(k = k, find_measure_name = self.find_measure_name(k), step_size = step_size))
        str.append(".measure dc {find_measure_name} param='{step_size}/(temp_ro1_{k}-temp_ro2_{k})'".format(k = k, find_measure_name = self.find_measure_name(k), step_size = step_size))
        
        return ["\n".join(str), ["temp_ro1_{k}".format(k=k), "temp_ro2_{k}".format(k=k)]]

    def rgate(self, ports, k):
        
        required_ports = ['g']
        self.check_prereqs(ports, required_ports)
        self.unit = 'ohms'
        self.type = 'ac'
        ac_stimulus = ['g']
        freq = self.get_defs(['frequency'])
        str = []
        str.append(self.get_instance_and_stimuli(k,ports,ac_stimulus))
        str.append(".measure ac yrgg_{k} find ir(vg_{k}) at {freq}".format(k = k, freq = freq))
        str.append(".measure ac yigg_{k} find ii(vg_{k}) at {freq}".format(k = k, freq = freq))
        str.append(".measure ac {find_measure_name} param='-1.0 * yrgg_{k}/(yigg_{k}*yigg_{k})'".format(find_measure_name = self.find_measure_name(k), k =k))

        return ["\n".join(str), ["yrgg_{k}".format(k=k), "yigg_{k}".format(k=k)]]

    def mos_ft(self, ports, k):
        
        required_ports = ['d', 'g']
        self.check_prereqs(ports, required_ports)
        self.unit = None
        self.type = 'ac'
        ac_stimulus = ['g']
        freq = self.param_data['definitions']['frequency']

        str = []
        str.append(self.get_instance_and_stimuli(k,ports,ac_stimulus))
        str.append(".measure ac mag_id_{k} find 'im(vd_{k})' at {freq}".format(k = k, freq = freq))
        str.append(".measure ac mag_ig_{k} find 'im(vg_{k})' at {freq}".format(k = k, freq = freq))
        str.append(".measure ac {find_measure_name} param='{freq} * mag_id_{k} / mag_ig_{k}'".format(find_measure_name = self.find_measure_name(k), k =k, freq = freq))

        return ["\n".join(str), ["mag_id_{k}".format(k=k), "mag_ig_{k}".format(k=k)]]


    def mismatch(self, analysis, ports, k):
        str = []
        measVars = []
        self.mm_analysis(str, analysis, ports, "{k}_a", measVars)
        self.mm_analysis(str, analysis, ports, "{k}_b", measVars)

        # self.type = str[0].match(/.measure\s*[a-z]*\s/i)[0].split('  ')[1]
        if self.param_data['definitions']['units'] == "%":
            param_str = "200*({measure_name}__a-{measure_name}__b)/({measure_name}__a+{measure_name}__b)"
            str.append(".measure {type} {@measure_name} param='{param_str}'")
        else:
            str.append(".measure {type} {@measure_name} param='{@measure_name}__a-{@measure_name}__b'")
        
        return ["\n".join(str), measVars+["{measure_name}__a", "{measure_name}__b"]]

    def mm_analysis(self, str, analysis, ports, var, measVars):
        
        if analysis is not None:
            tmp = getattr(self, analysis)(analysis,ports,var)
            print("hi")
        else:
            analysis = self.find_analysis_func(analysis)
            tmp = getattr(self, analysis)(ports, var)
        
        if type(tmp) == 'list':
            measVars.append(tmp[1])
            str.append(tmp[0])
        else:
            str.append(tmp)
        str << "\n"
        return


    def cgc(self,  ports, k):
        return self.simple_ac(["simple_ac","cg_sd"],ports,k)

    def simple_ac(self, analysis, ports, k):
        
        analysis_type, iports, oports = self.unpack_analysis(analysis,ports)
        required_ports = list(set((iports+oports)))
        self.check_prereqs(ports, required_ports)
        ac_stimulus = oports
        string = []
        string.append(self.get_instance_and_stimuli(k,ports,ac_stimulus))

        if iports == oports:
            ac_mult = "-1.0"
        else:
            ac_mult = "1.0"

        ac_str_ii = []
        ac_str_ir = []
        freq = self.get_defs(['frequency'])
        if len(iports) > 1:
            for port in iports:
                for each in oports:
                    if each == port:
                        print("Cannot fire and read on the same port when using multiple ports.")
                        exit
                    else:
                        ac_str_ii.append("ii_{port}_{k} find ii(v{port}_{k}) at {freq}".format(k = k, port = port, freq = freq))
                        ac_str_ir.append("ir_{port}_{k} find ir(v{port}_{k}) at {freq}".format(k = k, port = port, freq = freq))
            string.append(".measure ac ii_{k} param='{ac_str_ii.join("+")}'".format(k))
            string.append(".measure ac ir_{k} param='{ac_str_ir.join("+")}'".format(k))
        else:
            string.append(".measure ac ii_{k} find ii(v{iports}_{k}) at {freq}".format(k=k, iports = iports[0], freq = freq))
            string.append(".measure ac ir_{k} find ir(v{iports}_{k}) at {freq}".format(k=k, iports = iports[0], freq = freq))
        
        if analysis_type == 'cs':
            string.append(".measure ac {find_measure_name} param='ii_{k} / ({ac_mult}*2*3.141592654*{freq}*1.0) * (1+ir_{k}/ii_{k}*ir_{k}/ii_{k})'".format(k = k, find_measure_name = self.find_measure_name(k), ac_mult = ac_mult, freq = freq))
            self.unit = 'f'
        elif analysis_type == 'c' or 'cp':
            string.append(".measure ac {find_measure_name} param='ii_{k} / ({ac_mult}*2*3.141592654*{freq}*1.0)'".format(k = k, find_measure_name = self.find_measure_name(k), ac_mult = ac_mult, freq = freq))
            self.unit = 'f'
        elif analysis_type == 'ls':
            string.append(".measure ac {find_measure_name} param='-1.0 / ({ac_mult}*2*3.141592654*{freq}*ii_{k}) / (1+ir_{k}/ii_{k}*ir_{k}/ii_{k})'".format(k = k, find_measure_name = self.find_measure_name(k), ac_mult = ac_mult, freq = freq))
            self.unit = 'h'
        elif analysis_type == 'l' or 'lp':
            string.append(".measure ac {find_measure_name} param='-1.0 / ({ac_mult}*2*3.141592654*{freq}*ii_{k})'".format(k = k, find_measure_name = self.find_measure_name(k), ac_mult = ac_mult, freq = freq))
            self.unit = 'h'
        elif analysis_type == 'rp':
            string.append(".measure ac {find_measure_name} param='1.0/ir_{k}'".format(k = k, find_measure_name = self.find_measure_name(k)))
            self.unit = 'ohms'
        elif analysis_type == 'rs':
            string.append(".measure ac {find_measure_name} param='1.0*ir_{k}/(ir_{k}*ir_{k}+ii_{k}*ii_{k})'".format(k = k, find_measure_name = self.find_measure_name(k)))
            self.unit = 'ohms'
        elif analysis_type == 'q':
            string.append(".measure ac {find_measure_name} param='abs(ii_{k}/ir_{k})'".format(k = k, find_measure_name = self.find_measure_name(k)))
            self.unit = None
        elif analysis_type == 'yr':
            string.append(".measure ac {find_measure_name} param='ir_{k}'".format(k = k, find_measure_name = self.find_measure_name(k)))
            self.unit = 's'
        elif analysis_type == 'yi':
            string.append(".measure ac {find_measure_name} param='ii_{k}'".format(k = k, find_measure_name = self.find_measure_name(k)))
            self.unit = 's'
        else:
            raise KeyError("Invalid Parameter Type: {analysis}".format(analysis))
        self.type = 'ac'
        return ["\n".join(string), ["ii_{k}".format(k=k), "ir_{k}".format(k=k)]+ ac_str_ii + ac_str_ir]

    def dcres(self, analysis, ports, k):
        
        analysis_type, iports, oports = self.unpack_analysis(analysis, ports)
        required_ports = list(set((iports+oports)))
        self.check_prereqs(ports, required_ports)
        self.unit = 'ohms'
        self.type = 'dc'
        str = []
        str.append(self.get_instance_and_stimuli(k,ports,[]))
        if len(iports) != 1 or len(oports) != 1:
            raise "Only two ports allowed for resistance analysis."
        current_source = self.find_port_stimulus(iports[0])
        if iports == oports:
            str.append(".measure dc {find_measure_name} param='abs((v({iports}_{k}))/i({current_source}_{k}))'".format(find_measure_name = self.find_measure_name(k), iports = iports[0], k = k, current_source = current_source))
        else:
            str.append(".measure dc {find_measure_name} param='abs((v({iports}_{k},{oports}_{k}))/i({current_source}_{k}))'".format(find_measure_name = self.find_measure_name(k), iports = iports[0], oports = oports[0], k = k, current_source = current_source))
        return "\n".join(str)
    
    def find_measure_name(self, k):
        if '_' in str(k):
            #string = self.measure_name + "__" + str(k).split("_")[1]
            string = self.measure_name + "__" + str(k)
        else:
            string = self.measure_name
        return string
    def simple_voltage(self, analysis, ports, k):
        
        analysis_type, iports, oports = self.unpack_analysis(analysis, ports)
        required_ports = list(set((iports+oports)))
        self.check_prereqs(ports, required_ports)
        self.unit = 'v'
        self.type = 'dc'
        str = []
        str.append(self.get_instance_and_stimuli(k, ports, []))
        if len(iports) != 1 or len(oports) != 1:
            raise "Only two ports allowed for resistance analysis."
        if iports == oports:
            str.append(".measure dc {find_measure_name} param='v({iports}_{k})'".format(find_measure_name = self.find_measure_name(k), iports =iports[0], k = k))
        else:
            str.append(".measure dc {find_measure_name} param='v({iports}_{k},{oports}_{k})'".format(find_measure_name = self.find_measure_name(k), iports = iports[0], oports = oports[0], k = k))
        
        return "\n".join(str)

    def simple_current(self, analysis, ports, k):
        
        self.unit = 'a'
        self.type = 'dc'
        str = []
        str.append(self.get_instance_and_stimuli(k, ports, []))
        node = analysis[1][1:]
        current_source = self.find_port_stimulus(node)
        if not current_source:
            raise KeyError("Cannot find stimulis for node {node}".format(node))
        str.append(".measure dc {find_measure_name} param='-1*i({current_source}_{k})'".format(find_measure_name = self.find_measure_name(k), current_source = current_source, k = k))
        return "\n".join(str)

    def simple_current_sweep(self, analysis, ports, k):
        """

        Args:
            analysis (List[str]): [unused, i<port>]  
            ports (str): list of ports
            k (str): Instance number

        Raises:
            MeasureError: 
            KeyError: 

        Returns: <str> Netlist for a single sweep metric.  One instance per secondary sweep, plus measures for every point on the curve using a dependent voltage source on the first order of the sweep.
            
        """
        self.unit = 'a'
        self.type = 'dc'
        string = []
        if not self.param_data.get('sweep'):
            raise(MeasureError("Sweep analysis has no sweep"))
        
        sweeps = self.param_data['sweep']
        self.param_data['_additional_sweep_measures'] = True
        string.append(self.get_instance_and_stimuli(k, ports, []))
        node = analysis[1][1:]
        current_source = self.find_port_stimulus(node)
        if not current_source:
            raise KeyError(f"Cannot find stimulis for node {node}")
        if current_source == sweeps[1]:
            current_source='e'+ current_source[1:]
        sweep_stimulus = self.param_data['sweep'].get(1)
        sweep_node = sweep_stimulus[1:]
        sweep_dict = self.param_data['stimuli'][sweep_stimulus]
        for k_new,point in expand_generic_sweep(sweep_dict,k):
            if point<1e-14:
                point = 0
            string.append(f".measure dc {self.find_measure_name(k_new)} FIND '-1*i({current_source}_{k})' WHEN v({sweep_node}_{k})={point:.5g}")
        return "\n".join(string)

    def simple_tran(self, analysis, ports, k):
        
        self.unit = None
        str = []
        
        actual_analysis = re.sub(r'^t', "", analysis)
        analysis_str = ""
        if hasattr(self, actual_analysis):
            analysis_str = getattr(self, actual_analysis)(ports, k)
        else:
            func, analysis = self.find_analysis_func(actual_analysis)
            analysis_str = getattr(self, func)(analysis, ports, k)

        analysis_str = re.sub('dc', 'tran', analysis_str)
        analysis_str = re.sub('ac', 'tran', analysis_str)
        self.type = 'tran'
        str.append("{analysis_str} at {paramdata}".format(analysis_str = analysis_str, paramdata = self.param_data['definitions']['tstop']))
        return "\n".join(str)

    def stress(self, ports, k):
        str = []
        str.append(self.get_instance_and_stimuli(k, ports, [], 'stress'))
        return "\n".join(str)

    def to_titan(self,string, meas_vars = []):
        string = re.sub(r'\bfind\b', 'value=', string)
        string = re.sub(r'\bFIND\b', 'VALUE=', string)
        string = re.sub(r'\bwhen\b', 'targ', string)
        string = re.sub(r'\bWHEN\b', 'TARG', string)
        string = re.sub(r'\bparam\s*=\s*', 'value= ', string)
        string = re.sub(r'\bat\b', 'targ xvar =', string)
        string = self.replaceSpiceFunc(string,r'im\(', 'abs(i(', ')')
        string = self.replaceSpiceFunc(string,r'ii\(', "'im(i(", ')')
        string = self.replaceSpiceFunc(string,r'ir\(', "'re(i(", ')')
        
        if meas_vars:
            for meas in flatten(meas_vars):
                found = re.search(r'\.measure\s*[a-z]*\s*{}\b'.format(meas), string)
                if found:
                    offset = len(re.findall(r'\.measure\s*[a-z]*\s*{}\b'.format(meas), string)[0])
                    tmp = string[found.start() + offset:]
                    tmp = re.sub(r'\b{}\b'.format(meas), 'm({})'.format(meas), tmp)
                    string = string[:found.end()] + tmp
        return string
        
    def replaceSpiceFunc(self,string, find, replace, close):
        iiPos = re.search(find,string)
        while iiPos:
            find, replace = (replace, find)
            endPos = iiPos + len(replace)
            open = replace.count('(') - close.count(')')
            while open != 0:
                if string[endPos] == '(':
                    open = open + 1
                if string[endPos] == ')':
                    open = open - 1
                endPos = endPos + 1
            string[endPos] = close
            iiPos = endPos + string[endPos - 1][find]

        return string
