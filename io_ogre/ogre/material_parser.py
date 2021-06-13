
import bpy
import os
import ast
import logging

logger = logging.getLogger('material_parser')

class ScriptToken:
    TID_LBRACKET = 0
    TID_RBRACKET = 1
    TID_COLON = 2
    TID_VARIABLE = 3
    TID_WORD = 4
    TID_QUOTE = 5
    TID_NEWLINE = 6
    TID_UNKNOWN = 7
    TID_END = 8

    types = ["TID_LBRACKET", "TID_RBRACKET", "TID_COLON", "TID_VARIABLE", "TID_WORD", "TID_QUOTE", "TID_NEWLINE", "TID_UNKNOWN", "TID_END"]

    def __init__(self, line):
        self.line = line
        self.type = -1
        self.lexeme = ""

    def __str__(self):
        return("line: %s, type: %s, lexeme: %s" % (self.line, self.types[self.type], self.lexeme))

class ScriptLexer:

    error = ""
    
    def tokenize(self, str, source):

        # States
        READY = 0
        COMMENT = 1
        MULTICOMMENT = 2
        WORD = 3
        QUOTE = 4
        VAR = 5
        POSSIBLECOMMENT = 6

        # Set up some constant characters of interest
        varopener = '$'
        quote = '"'
        slash = '/'
        backslash = '\\'
        openbrace = '{'
        closebrace = '}'
        colon = ':'
        star = '*'
        cr = '\r'
        lf = '\n'

        c = 0
        lastc = 0

        lexeme = ""
        line = 1
        state = READY
        lastQuote = 0
        firstOpenBrace = 0
        braceLayer = 0
        tokens = []

        # Iterate over the input
        for i in str:
        
            lastc = c;
            c = i;
            
            if c == quote:
                lastQuote = line;
            
            if state == READY or state == WORD or state == VAR:
                if c == openbrace:
                    if braceLayer == 0:
                        firstOpenBrace = line;
                    braceLayer += 1

                elif c == closebrace:
                    if braceLayer == 0:
                        self.error = "no matching open bracket '{' found for close bracket '}' at %s:%s" % (source, line)
                        return tokens;
                    braceLayer -= 1
            
            if state == READY:
                if c == slash and lastc == slash:
                    # Comment start, clear out the lexeme
                    lexeme = ""
                    state = COMMENT

                elif c == star and lastc == slash:
                    lexeme = ""
                    state = MULTICOMMENT

                elif c == quote:
                    # Clear out the lexeme ready to be filled with quotes!
                    lexeme = c
                    state = QUOTE

                elif c == varopener:
                    # Set up to read in a variable
                    lexeme = c
                    state = VAR

                elif self.isNewline(c):
                    lexeme = c
                    self.setToken(lexeme, line, tokens)

                elif not self.isWhitespace(c):
                    lexeme = c
                    if c == slash:
                        state = POSSIBLECOMMENT
                    else:
                        state = WORD

            elif state == COMMENT:
                if self.isNewline(c):
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

            elif state == MULTICOMMENT:
                if c == slash and lastc == star:
                    state = READY

            elif state == POSSIBLECOMMENT:
                if c == slash and lastc == slash:
                    lexeme = ""
                    state = COMMENT

                elif c == star and lastc == slash:
                    lexeme = ""
                    state = MULTICOMMENT

                else:
                    state = WORD
                    # OGRE_FALLTHROUGH;

            elif state == WORD:
                if self.isNewline(c):
                    self.setToken(lexeme, line, tokens)
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

                elif self.isWhitespace(c):
                    self.setToken(lexeme, line, tokens)
                    state = READY

                elif c == openbrace or c == closebrace or c == colon:
                    self.setToken(lexeme, line, tokens)
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

                else:
                    lexeme += c

            elif state == QUOTE:
                if c != backslash:
                    # Allow embedded quotes with escaping
                    if c == quote and lastc == backslash:
                        lexeme += c

                    elif c == quote:
                        lexeme += c
                        self.setToken(lexeme, line, tokens)
                        state = READY

                    else:
                        # Backtrack here and allow a backslash normally within the quote
                        if lastc == backslash:
                            lexeme = lexeme + "\\" + c
                        else:
                            lexeme += c

            elif state == VAR:
                if isNewline(c):
                    self.setToken(lexeme, line, tokens)
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

                elif isWhitespace(c):
                    self.setToken(lexeme, line, tokens)
                    state = READY

                elif c == openbrace or c == closebrace or c == colon:
                    self.setToken(lexeme, line, tokens)
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

                else:
                    lexeme += c

            # Separate check for newlines just to track line numbers
            if (c == cr or (c == lf and lastc != cr)):
                line += 1

        # Check for valid exit states
        if state == WORD or state == VAR:
            if lexeme != "":
                self.setToken(lexeme, line, tokens)

        else:
            if state == QUOTE:
                self.error = "no matching \" found for \" at %s:%s" % (source, lastQuote)
                return tokens;
        
        # Check that all opened brackets have been closed
        if braceLayer == 1:
            self.error = "no matching closing bracket '}' for open bracket '{' at %s:%s" % (source, firstOpenBrace)

        elif braceLayer > 1:
            self.error = "too many open brackets (%d) '{' without matching closing bracket '}' in %s" % (braceLayer, source)

        return tokens;

    def setToken(self, lexeme, line, tokens):
        openBracket = '{'
        closeBracket = '}'
        colon = ':'
        quote = '\"'
        var = '$'

        token = ScriptToken(line)
        token.line = line
        ignore = False

        # Check the user token map first
        if(len(lexeme) == 1 and self.isNewline(lexeme[0])):
            token.type = ScriptToken.TID_NEWLINE

            if(len(tokens) != 0 and tokens[-1].type == ScriptToken.TID_NEWLINE):
                ignore = True

        elif(len(lexeme) == 1 and lexeme[0] == openBracket):
            token.type = ScriptToken.TID_LBRACKET

        elif(len(lexeme) == 1 and lexeme[0] == closeBracket):
            token.type = ScriptToken.TID_RBRACKET

        elif(len(lexeme) == 1 and lexeme[0] == colon):
            token.type = ScriptToken.TID_COLON

        else:
            token.lexeme = lexeme

            # This is either a non-zero length phrase or quoted phrase
            if(len(lexeme) >= 2 and lexeme[0] == quote and lexeme[-1] == quote):
                token.type =ScriptToken.TID_QUOTE

            elif(len(lexeme) > 1 and lexeme[0] == var):
                token.type = ScriptToken.TID_VARIABLE

            else:
                token.type = ScriptToken.TID_WORD

        if(not ignore):
            tokens.append(token)

    def isWhitespace(self, c):
        return (c == ' ' or c == '\r' or c == '\t')

    def isNewline(self, c):
        return (c == '\n' or c == '\r')


class MaterialParser:

    def unquote(string):
        return (string[1:-1])
    

    def parameters(i, tokens):
        parameters = []
        j = 1
        while tokens[i + j].type == ScriptToken.TID_WORD:

            try:
                lexeme = ast.literal_eval(tokens[i + j].lexeme)

            except ValueError:
                lexeme = tokens[i + j].lexeme

            except SyntaxError:
                lexeme = tokens[i + j].lexeme
            
            parameters.append(lexeme)

            j += 1
        
        return parameters


    def xParseMaterial(meshMaterials, materialFile, folder):
        logger.info("* Parsing material file: %s" % materialFile)

        try:
            filein = open(materialFile)
        except Exception:
            logger.warning("Material: File %s not found!" % materialFile)
            return None

        data = filein.read()
        filein.close()
        
        sl = ScriptLexer()
        tokens = sl.tokenize(data, materialFile)
        
        if sl.error != "":
            logger.error("ERROR: Material Script tokenizer failed with error: %s" % sl.error)
            return None

        SID_NONE = -1
        SID_MATERIAL = 0
        SID_TECHNIQUE = 1
        SID_PASS = 2
        SID_TEXTURE_UNIT = 3

        state = SID_NONE
        
        # TODO:
        # - RTSS Support

        for i in range(0, len(tokens)):
            token = tokens[i]

            # Find Material
            if state == SID_NONE:
                if token.type == ScriptToken.TID_WORD and token.lexeme == "import":
                    logger.warning("Script importing and material inheritance are not supported")

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "vertex_program":
                    logger.warning("Vertex programs not supported, only Fixed Function Pipeline style materials")

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "fragment_program":
                    logger.warning("Fragment programs not supported, only Fixed Function Pipeline style materials")

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "geometry_program":
                    logger.warning("Geometry programs not supported, only Fixed Function Pipeline style materials")
            
                elif token.type == ScriptToken.TID_WORD and token.lexeme == "material":
                    technique_nr = 0
                    pass_nr = 0
                    name = ""
                    Material = {}

                    state = SID_MATERIAL
                    
                    if tokens[i + 1].type == ScriptToken.TID_WORD:
                        name = tokens[i + 1].lexeme

                    elif tokens[i + 1].type == ScriptToken.TID_QUOTE:
                        name = MaterialParser.unquote(tokens[i + 1].lexeme)
                    
                    else:
                        logger.error("ERROR: Material name not found %s" % token)
                        continue

                    logger.debug("Material name: %s" % name)
            
            # Parse Material
            elif state == SID_MATERIAL:
                if token.type == ScriptToken.TID_WORD and token.lexeme == "technique":
                    state = SID_TECHNIQUE

                    technique_nr += 1
                    
                    if technique_nr > 1:
                        logger.warning("Only one technique is supported")

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "receive_shadows":
                    if tokens[i + 1].type == ScriptToken.TID_WORD and tokens[i + 1].lexeme == "on":
                        logger.debug("receive_shadows: %s" % tokens[i + 1].lexeme)
                        Material['receive_shadows'] = True
                        # context.material.use_shadows = True

                    elif tokens[i + 1].type == ScriptToken.TID_WORD and tokens[i + 1].lexeme == "off":
                        logger.debug("receive_shadows: %s" % tokens[i + 1].lexeme)
                        Material['receive_shadows'] = False
                        # context.material.use_shadows = False
                    
                    else:
                        logger.error("Parsing receive_shadows %s" % token)
                
                elif token.type == ScriptToken.TID_RBRACKET:
                    state = SID_NONE
                    
                    if len(Material) > 0:
                        meshMaterials[name] = Material
                    else:
                        logger.warning("Material %s is empty" % name)

            # Parse Technique
            elif state == SID_TECHNIQUE:
                if technique_nr > 1 and token.type != ScriptToken.TID_RBRACKET:
                    continue

                if token.type == ScriptToken.TID_WORD and token.lexeme == "pass":
                    state = SID_PASS

                    pass_nr += 1
                    
                    if pass_nr > 1:
                        logger.warning("Only one pass is supported")

                elif token.type == ScriptToken.TID_RBRACKET:
                    state = SID_MATERIAL

            # Parse Pass
            elif state == SID_PASS:
                if pass_nr > 1 and token.type != ScriptToken.TID_RBRACKET:
                    continue
            
                if token.type == ScriptToken.TID_WORD and token.lexeme == "texture_unit":
                    state = SID_TEXTURE_UNIT

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "ambient":
                    params = MaterialParser.parameters(i, tokens)
                    
                    if len(params) == 1 and tokens[i + 1].lexeme == "vertexcolour":
                        Material['vertexcolour'] = True
                        #context.material.use_vertex_color_paint = True
                
                    elif len(params) == 3 or len(params) == 4:
                        Material['ambient'] = params

                    else:
                        logger.error("Parsing ambient: %s" % token)

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "diffuse":
                    params = MaterialParser.parameters(i, tokens)
                    
                    if len(params) == 1 and tokens[i + 1].lexeme == "vertexcolour":
                        Material['vertexcolour'] = True
                        #context.material.use_vertex_color_paint = True

                    elif len(params) == 3 or len(params) == 4:
                        Material['diffuse'] = params

                    else:
                        logger.error("Parsing diffuse: %s" % token)

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "specular":
                    params = MaterialParser.parameters(i, tokens)
                    
                    if len(params) == 1 and tokens[i + 1].lexeme == "vertexcolour":
                        Material['vertexcolour'] = True
                        #context.material.use_vertex_color_paint = True

                    elif len(params) == 3 or len(params) == 4 or len(params) == 5:
                        Material['specular'] = params
                        #print("\t\tspecular: %s" % params)

                    else:
                        logger.error("Parsing specular: %s" % token)

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "emissive":
                    params = MaterialParser.parameters(i, tokens)
                    
                    if len(params) == 1 and tokens[i + 1].lexeme == "vertexcolour":
                        Material['vertexcolour'] = True
                        #context.material.use_vertex_color_paint = True

                    elif len(params) == 3 or len(params) == 4:
                        Material['emissive'] = params
                        #emit_intensity = (color[0] * 0.2126 + color[1] * 0.7152 + color[2] * 0.0722) * color[3];
                        #emit_intensity = color[0] * 0.2126 + color[1] * 0.7152 + color[2] * 0.0722;
                    else:
                        logger.error("Parsing emissive: %s" % token)

                elif token.type == ScriptToken.TID_WORD and token.lexeme == "depth_bias":
                    params = MaterialParser.parameters(i, tokens)
                    
                    if len(params) == 1:
                        Material['depth_bias'] = params
                        # mat.offset_z = tokens[i + 1].lexeme
                    else:
                        logger.error("Parsing depth_bias: %s" % token)

                elif token.type == ScriptToken.TID_RBRACKET:
                    state = SID_TECHNIQUE
            
            elif state == SID_TEXTURE_UNIT:
                if token.type == ScriptToken.TID_WORD and token.lexeme == "texture":
                    if tokens[i + 1].type == ScriptToken.TID_WORD:
                        imageName = tokens[i + 1].lexeme

                    elif tokens[i + 1].type == ScriptToken.TID_QUOTE:
                        imageName = self.unquote(tokens[i + 1].lexeme)
                    
                    else:
                        logger.error("Texture name not found: %s" % token)
                        continue
                        
                    file = os.path.join(folder, imageName)
                    if(not os.path.isfile(file)):
                        # Just force to use .dds if there isn't a file specified in the material file
                        file = os.path.join(folder, os.path.splitext(imageName)[0] + ".dds")
                        if(os.path.isfile(file)):
                            Material['texture'] = file
                            Material['imageNameOnly'] = imageName
                        else:
                            logger.warning("Referenced texture '%s' not found" % imageName)
                    else:
                        Material['texture'] = file
                        Material['imageNameOnly'] = imageName
            
                elif token.type == ScriptToken.TID_RBRACKET:
                    state = SID_PASS


    def xCollectMaterialData(meshData, onlyName, folder):

        meshMaterials = {}
        nameDotMaterial = onlyName + ".material"
        pathMaterial = os.path.join(folder, nameDotMaterial)
        if not os.path.isfile(pathMaterial):
            # Search directory for .material
            for filename in os.listdir(folder):
                if ".material" in filename:
                    # Material file
                    pathMaterial = os.path.join(folder, filename)
                    MaterialParser.xParseMaterial(meshMaterials, pathMaterial, folder)
        else:
            MaterialParser.xParseMaterial(meshMaterials, pathMaterial, folder)
        
        meshData['materials'] = meshMaterials
