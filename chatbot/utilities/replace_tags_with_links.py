import glob
import os
import logging
import chardet
from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline



def hashtag_rule(state: StateInline, silent: bool):
    if state.src[state.pos] != '#':
        return False
    if state.pos > 0 and state.src[state.pos - 1] != ' ':
        return False
    start = state.pos + 1
    while start < len(state.src) and state.src[start].isalnum():
        start += 1
    if start == state.pos + 1:
        return False
    if not silent:
        token = state.push('hashtag_open', 'a', 1)
        token.attrs = {'href': '/tags/' + state.src[state.pos + 1:start]}
        token = state.push('text', '', 0)
        token.content = state.src[state.pos + 1:start]
        state.push('hashtag_close', 'a', -1)
    state.pos = start
    return True


md = MarkdownIt()
md.inline.ruler.before('text', 'hashtag', hashtag_rule)


def replace_tags_with_links(filename):
    try:
        with open(filename, 'rb') as f:
            rawdata = f.read()

        result = chardet.detect(rawdata)
        charenc = result['encoding']

        with open(filename, 'r', encoding=charenc) as file:
            content = file.read()
            new_content = md.render(content)

        new_filename = f'{filename[:-3]}_modified.md'
        with open(new_filename, 'w', encoding='utf-8') as new_file:
            new_file.write(new_content)

        print(f'Successfully processed {filename}')
    except Exception as e:
        print(f'Error processing {filename}: {str(e)}')


def crawl_folders_and_replace_tags(path):
    try:
        for dirpath, dirs, files in os.walk(path):
            for filename in glob.glob(os.path.join(dirpath, '*.md')):
                replace_tags_with_links(filename)

        print(f'Successfully crawled folders and replaced tags in path: {path}')
    except Exception as e:
        print(f'Error crawling folders and replacing tags in path: {path}, Error: {str(e)}')


if __name__ == "__main__":
    try:
        crawl_folders_and_replace_tags(
            r'D:\Dropbox\Northeastern\Courses\neural_control_of_real_world_human_movement\main_course_repo\docs\CourseObsidianVault')
        print('Completed process successfully.')
    except Exception as e:
        print(f'Error in main execution: {str(e)}')
