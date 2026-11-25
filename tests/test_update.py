"""Dependency-free behavior checks; not a Home Assistant integration test."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/alsavopro'

def load_method(file, cls, method, env):
    tree = ast.parse((ROOT/file).read_text())
    node = next(n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == cls
                for n in c.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == method)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT/file), 'exec'), env)
    return env[method]

class Tests(unittest.TestCase):
    def test_activity_matrix(self):
        action=NS(OFF='off', IDLE='idle', HEATING='heating', COOLING='cooling', DEFROSTING='defrosting')
        method=load_method('climate.py','AlsavoProClimate','hvac_action',{'HVACAction':action})
        for online,power,code,hz,expected in [
            (False,True,3,50,None),(True,False,3,50,'off'),
            (True,True,1,0,'idle'),(True,True,2,50,'defrosting'),
            (True,True,3,50,'heating'),(True,True,4,50,'cooling'),
            (True,True,3,0,'idle'),(True,True,4,0,'idle'),
            (True,True,5,50,None),(True,True,0,0,None),(True,True,99,50,None)]:
            with self.subTest(code=code,hz=hz,power=power,online=online):
                handler=NS(is_power_on=power,get_status_value=lambda idx: {53:code,27:hz}[idx])
                self.assertEqual(method(NS(available=online,_data_handler=handler)),expected)

    def test_reconfigure(self):
        # Fake only the framework boundary; execute the actual reconfigure method.
        vol=NS(Schema=lambda x:x, Required=lambda key,**kw:key,Optional=lambda key,**kw:key)
        env=dict(vol=vol,DOMAIN='alsavopro',SERIAL_NO='serial_no',CONF_NAME='name',
                 CONF_PASSWORD='password',CONF_IP_ADDRESS='ip_address',CONF_PORT='port',DEFAULT_LOCAL_PORT='1194')
        method=load_method('config_flow.py','ConfigFlow','async_step_reconfigure',env)
        original=dict(name='Pool',serial_no='123',ip_address='192.168.1.10',port='1194',password='secret')
        entry=NS(entry_id='existing',data=original)
        entries=[entry]
        flow=NS(_get_reconfigure_entry=lambda:entry,
                hass=NS(config_entries=NS(async_entries=lambda domain:entries)),
                async_show_form=lambda **kw:kw,
                async_update_reload_and_abort=lambda target,**kw:(target,kw))
        form=asyncio.run(method(flow))
        self.assertEqual(form['step_id'],'reconfigure')
        changed={**original,'name':'New name','serial_no':'456','ip_address':'192.168.1.20','password':''}
        target,result=asyncio.run(method(flow,changed))
        self.assertIs(target,entry)
        data=result['data_updates']
        self.assertEqual(data['password'],'secret')
        self.assertEqual(data['entity_identity'],'Pool_123')
        self.assertEqual(data['device_identity'],'123')
        self.assertEqual(data['ip_address'],'192.168.1.20')
        self.assertEqual(original['name'],'Pool')
        entry.data=data
        target,result=asyncio.run(method(flow,{**changed,'name':'Third name','password':'newpass'}))
        self.assertEqual(result['data_updates']['entity_identity'],'Pool_123')
        self.assertEqual(result['data_updates']['password'],'newpass')
        for key,value in [('port','70000'),('port','abc'),('serial_no','bad'),('name',' '),('ip_address',' ')]:
            with self.subTest(key=key):
                result=asyncio.run(method(flow,{**changed,key:value}))
                self.assertEqual(result['errors']['base'],'invalid_details')
        entries.append(NS(entry_id='other',data={'serial_no':'456'}))
        self.assertEqual(asyncio.run(method(flow,changed))['errors']['base'],'already_configured')

if __name__=='__main__':
    unittest.main()
