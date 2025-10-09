from setuptools import setup, find_packages

setup(
    name='ckanext-doi-import',
    version='0.1.0',
    description='CKAN extension for importing datasets from DOI',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/ckanext-doi-import',
    packages=find_packages(),
    namespace_packages=['ckanext'],
    install_requires=[
        'requests',
    ],
    entry_points={
        'ckan.plugins': [
            'doi_import = ckanext.doi_import.plugin:DoiImportPlugin',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
    ],
)
