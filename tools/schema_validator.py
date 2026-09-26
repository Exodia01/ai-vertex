"""Minimal JSON Schema (draft 2020-12 subset) validator - stdlib only.

Supported: type (incl. arrays), properties, required, additionalProperties(bool),
enum, const, pattern, minimum, maximum, minItems, items, minLength, maxLength,
allOf, anyOf, oneOf, if/then/else, $ref to $defs, propertyNames.
Unsupported constructs are reported rather than silently ignored.
"""
import json, re

SUPPORTED={"$schema","$id","title","description","type","properties","required",
           "additionalProperties","enum","const","pattern","minimum","maximum",
           "minItems","items","minLength","maxLength","allOf","anyOf","oneOf",
           "if","then","else","$defs","$ref","propertyNames","format"}

def _type_ok(value,t):
    if t=="object":  return isinstance(value,dict)
    if t=="array":   return isinstance(value,list)
    if t=="string":  return isinstance(value,str)
    if t=="integer": return isinstance(value,int) and not isinstance(value,bool)
    if t=="number":  return isinstance(value,(int,float)) and not isinstance(value,bool)
    if t=="boolean": return isinstance(value,bool)
    if t=="null":    return value is None
    raise ValueError(f"unknown type {t}")

def _resolve(schema,root):
    seen=0
    while "$ref" in schema:
        ref=schema["$ref"]; seen+=1
        if seen>32: raise ValueError("$ref loop")
        if not ref.startswith("#/"): raise ValueError(f"unsupported $ref {ref}")
        node=root
        for part in ref[2:].split("/"):
            node=node[part]
        merged={k:v for k,v in schema.items() if k!="$ref"}
        schema={**node,**merged}
    return schema

def validate(instance, schema, root=None, path="$"):
    """Returns list of error strings. Empty list == valid."""
    root=root if root is not None else schema
    schema=_resolve(schema,root)
    errs=[]
    unknown=set(schema)-SUPPORTED
    if unknown: errs.append(f"{path}: unsupported schema keywords {sorted(unknown)}")
    if "type" in schema:
        types=schema["type"] if isinstance(schema["type"],list) else [schema["type"]]
        if not any(_type_ok(instance,t) for t in types):
            errs.append(f"{path}: expected type {schema['type']}, got {type(instance).__name__}")
            return errs
    if "const" in schema and instance!=schema["const"]:
        errs.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in enum {schema['enum']}")
    if isinstance(instance,str):
        if "pattern" in schema and not re.search(schema["pattern"],instance):
            errs.append(f"{path}: {instance!r} fails pattern {schema['pattern']!r}")
        if "minLength" in schema and len(instance)<schema["minLength"]:
            errs.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance)>schema["maxLength"]:
            errs.append(f"{path}: longer than maxLength {schema['maxLength']}")
    if isinstance(instance,(int,float)) and not isinstance(instance,bool):
        if "minimum" in schema and instance<schema["minimum"]:
            errs.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance>schema["maximum"]:
            errs.append(f"{path}: {instance} > maximum {schema['maximum']}")
    if isinstance(instance,list):
        if "minItems" in schema and len(instance)<schema["minItems"]:
            errs.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "items" in schema:
            for i,item in enumerate(instance):
                errs+=validate(item,schema["items"],root,f"{path}[{i}]")
    if isinstance(instance,dict):
        for r in schema.get("required",[]):
            if r not in instance: errs.append(f"{path}: missing required '{r}'")
        props=schema.get("properties",{})
        for k,v in instance.items():
            if k in props: errs+=validate(v,props[k],root,f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: additional property '{k}' not allowed")
        if "propertyNames" in schema:
            for k in instance: errs+=validate(k,schema["propertyNames"],root,f"{path}.<key {k}>")
    for sub in schema.get("allOf",[]): errs+=validate(instance,sub,root,path)
    if "anyOf" in schema:
        if not any(not validate(instance,s,root,path) for s in schema["anyOf"]):
            errs.append(f"{path}: matched none of anyOf")
    if "oneOf" in schema:
        hits=sum(1 for s in schema["oneOf"] if not validate(instance,s,root,path))
        if hits!=1: errs.append(f"{path}: matched {hits} of oneOf, expected exactly 1")
    if "if" in schema:
        if not validate(instance,schema["if"],root,path):
            if "then" in schema: errs+=validate(instance,schema["then"],root,path)
        elif "else" in schema:
            errs+=validate(instance,schema["else"],root,path)
    return errs

def load(path):
    with open(path) as f: return json.load(f)
