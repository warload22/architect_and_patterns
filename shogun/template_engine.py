import os
import re
from typing import List
from shogun.request import Request


BASE_PATTERN = re.compile(r'{% extends (?P<base>[a-zA-Z_]+) %}')
BASE_BLOCK_PATTERN = re.compile(r'{% block [a-zA-Z_]+ %}')
INCLUDE_PATTERN = re.compile(r'{% include [a-zA-Z_]+ %}')
FOR_PATTERN = re.compile(r'{% [a-zA-Z_]+ : for [a-zA-Z_]+ in [a-zA-Z_]+ %}')
IF_PATTERN = re.compile(r'{% [a-zA-Z_]+ : if .+ %}')
VAR_PATTERN = re.compile(r'{{ (?P<variable>[a-zA-Z0-9_.\[\]"\']+) }}')


class Engine:

    def __init__(self, base_dir: str, templates_dir_name: str, includes_dir_name: str):
        self.template_dir = os.path.join(base_dir, templates_dir_name)
        self.include_dir = os.path.join(self.template_dir, includes_dir_name)

    def get_template_as_string(self, template_name: str, include: bool = False) -> str:
        template_path = os.path.join(self.template_dir, template_name)
        if include:
            template_path = os.path.join(self.include_dir, template_name)
        if not os.path.isfile(template_path):
            raise Exception(f'{template_path} is not a file')
        with open(template_path) as f:
            return f.read()

    @staticmethod
    def check_base(block: str) -> bool:
        return bool(BASE_PATTERN.search(block))

    @staticmethod
    def get_block_pattern(block_name: str):
        return re.compile(fr'{{% block {block_name} %}}(?P<content>[\S\s]+)(?={{% endblock {block_name} %}}){{% endblock {block_name} %}}')

    @staticmethod
    def get_if_pattern(block_name: str):
        return re.compile(
            fr'{{% {block_name} : if (?P<left_variable>.+) == (?P<right_variable>.+) %}}(?P<if_true>[\S\s]+)(?={{% else %}}){{% else %}}(?P<if_false>[\S\s]+)(?={{% endif {block_name} %}}){{% endif {block_name} %}}')

    @staticmethod
    def get_for_pattern(block_name: str):
        return re.compile(
            fr'{{% {block_name} : for (?P<variable>[a-zA-Z_]+) in (?P<seq>[a-zA-Z_]+) %}}(?P<content>[\S\s]+)(?={{% endfor {block_name} %}}){{% endfor {block_name} %}}')

    @staticmethod
    def get_blocks_names(block: str) -> List[str]:
        base_blocks = BASE_BLOCK_PATTERN.findall(block)
        return [i.replace('{% block ', '').replace(' %}', '') for i in base_blocks]

    @staticmethod
    def get_if_names(block: str) -> List[str]:
        used_if = IF_PATTERN.findall(block)
        return [i[3:i.find(':') - 1] for i in used_if]

    @staticmethod
    def get_for_names(block: str) -> List[str]:
        used_for = FOR_PATTERN.findall(block)
        return [i[3:i.find(':') - 1] for i in used_for]

    def build_includes(self, block: str) -> str:
        used_includes = INCLUDE_PATTERN.findall(block)
        if not used_includes:
            return block

        for inc in used_includes:
            inc_name = inc.replace('{% include ', '').replace(' %}', '')
            inc_block = self.get_template_as_string(f'{inc_name}.html', True)
            template_inc = f'{{% include {inc_name} %}}'
            block = re.sub(template_inc, inc_block, block)

        return block

    def build_base(self, template: str) -> str:
        base_name = BASE_PATTERN.search(template).group('base')
        base_block = self.get_template_as_string(f'{base_name}.html')
        base_blocks_names = self.get_blocks_names(base_block)

        for name in base_blocks_names:
            pattern = self.get_block_pattern(name)
            template_block = pattern.search(template)
            if template_block:
                base_block = re.sub(pattern, template_block.group('content'), base_block)
            else:
                base_block = re.sub(pattern, pattern.search(base_block).group('content'), base_block)

        return base_block

    @staticmethod
    def build_vars(context: dict, block: str) -> str:
        used_vars = VAR_PATTERN.findall(block)
        if not used_vars:
            return block

        for var in used_vars:
            template_var = '{{ %s }}' % var
            if var.find('.') != -1:
                variable = var[:var.find('.')]
                param = var[var.find('.') + 1:]
                context_var = str(context.get(variable, '').__getattribute__(param))
            else:
                context_var = str(context.get(var, ''))
            block = re.sub(template_var, context_var, block)

        return block

    def build_if(self, context: dict, block: str) -> str:
        if_names = self.get_if_names(block)

        for name in if_names:
            pattern = self.get_if_pattern(name)
            current_if = pattern.search(block)
            left_variable = self.build_vars(context, current_if.group('left_variable'))
            right_variable = self.build_vars(context, current_if.group('right_variable'))
            result = bool(left_variable == right_variable)
            build_if = current_if.group('if_true') if result else current_if.group('if_false')
            block = re.sub(pattern, build_if, block)

        return block

    def build_for(self, context: dict, block: str) -> str:
        for_names = self.get_for_names(block)

        for name in for_names:
            pattern = self.get_for_pattern(name)
            current_for = pattern.search(block)
            build_for = ''
            for i in context.get(current_for.group('seq'), []):
                build_if = self.build_if({**context, current_for.group('variable'): i}, current_for.group('content'))
                build_for += self.build_vars({**context, current_for.group('variable'): i}, build_if)
            block = re.sub(pattern, build_for, block)

        return block

    def build(self, context: dict, template_name: str) -> str:
        template = self.get_template_as_string(template_name)
        if self.check_base(template):
            template = self.build_base(template)
        template = self.build_includes(template)
        template = self.build_for(context, template)
        template = self.build_if(context, template)
        return self.build_vars(context, template)


def build_template(request: Request, context: dict, template_name: str) -> str:
    assert request.settings.get('BASE_DIR')
    assert request.settings.get('TEMPLATES_DIR_NAME')
    assert request.settings.get('INCLUDES_DIR_NAME')

    engine = Engine(request.settings.get('BASE_DIR'), request.settings.get('TEMPLATES_DIR_NAME'),
                    request.settings.get('INCLUDES_DIR_NAME'))
    return engine.build(context, template_name)
