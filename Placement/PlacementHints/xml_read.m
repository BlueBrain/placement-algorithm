function [tree, RootName, DOMnode] = xml_read(xmlfile, Pref)
% XML_READ reads xml files and converts them into Matlab's struct tree.
% 
% DESCRIPTION
% tree = xml_read(xmlfile) reads 'xmlfile' into data structure 'tree'
%
% tree = xml_read(xmlfile, Pref) reads 'xmlfile' into data structure 'tree'
% according to your preferences
%
% [tree, RootName, DOMnode] = xml_read(xmlfile) get additional information
% about XML file
%
% INPUT:
%  xmlfile	URL or filename of xml file to read
%  Pref     Preferences:
%    Pref.ItemName - default 'item' - name of a special tag used to itemize
%                    cell arrays
%    Pref.ReadAttr - default true - allow reading attributes
%    Pref.Str2Num - default true - convert strings that look like numbers 
%                   to numbers
%    Pref.NoCells - default true - force output to have no cell arrays
% OUTPUT:
%  tree         tree of structs and/or cell arrays coresponding to xml file
%  RootName     XML tag name used for root (top level) node
%  DOMnode      output of xmlread
%
% DETAILS:
% Function xml_read first calls MATLAB's xmlread function and than 
% converts its output ('Document Object Model' tree of Java objects) 
% to tree of MATLAB struct's. The output is often in format of nested 
% structs and cells. In the output data structure field names are based on
% XML tags, exept in cases when tags produce illegal variable names.
%
% EXAMPLES:
% xmlfile = fullfile(matlabroot, 'toolbox/matlab/general/info.xml');
%
% See also:
%   xml_write, xmlread, xmlwrite
%
% Written by Jarek Tuszynski, SAIC, jaroslaw.w.tuszynski_at_saic.com
% References:
%  - Function inspired by Example 3 found in xmlread function.
%  - Output data structures inspited by xml_toolbox structures.
  
%% default preferences
DPref.ItemName  = 'item'; % name of a special tag used to itemize cell arrays
DPref.ReadAttr  = true;   % allow reading attributes
DPref.Str2Num   = true;   % convert strings that look like numbers to numbers
DPref.NoCells   = true;   % force output to have no cell arrays
tree     = [];
RootName = [];

%% read user preferences
if (nargin>1)
  if (isfield(Pref, 'ItemName')), DPref.ItemName = Pref.ItemName; end
  if (isfield(Pref, 'ReadAttr')), DPref.ReadAttr = Pref.ReadAttr; end
  if (isfield(Pref, 'Str2Num' )), DPref.Str2Num  = Pref.Str2Num ; end
  if (isfield(Pref, 'NoCells' )), DPref.NoCells  = Pref.NoCells ; end
end

%% read xml file
try
  DOMnode = xmlread(xmlfile); 
catch
  error('Failed to read XML file %s.',xmlfile);
end

%% Find the Root node
RootNode = DOMnode.getFirstChild;
while (RootNode.getNodeType~=RootNode.ELEMENT_NODE)
  RootNode = RootNode.getNextSibling;
  if (isempty(RootNode)), return; end
end

%% parse xml file
%try
    [tree RootName] = DOMnode2struct(RootNode, DPref);
%catch
%  error('Unable to parse XML file %s.',xmlfile);
%end

  
  
%% =======================================================================
function [s sname] = DOMnode2struct(node, Pref)
sname = char(node.getNodeName); % capture name of the node
sname = genvarname(sname); % if sname is not a good variable name - fix it
s = [];
  
%% read in node data
if (node.getNodeType==node.TEXT_NODE)
  s = char(node.getData);
  if (all(StrIsNum(s)) && Pref.Str2Num), s = str2num(s); end
  return;
end
  
%% === read in children nodes ============================================
vec=[];
if (node.hasChildNodes)        % children present
  Child  = node.getChildNodes; % create array of children nodes
  nChild = Child.getLength;    % number of children
    
  % --- pass 1: how many children with each name ----------------------- 
  f = [];
  for iChild = 1:nChild        % read in each child
    cname = char(Child.item(iChild-1).getNodeName);
    cname = genvarname(cname);
    if (~strcmp(cname,'x0x23text'))
      if (~isfield(f,cname)), 
        f.(cname)=0;           % initialize first time I see this name
      end  
      f.(cname) = f.(cname)+1; % add to the counter
    end
  end                          % end for iChild
    
  % --- pass 2: store all the children ---------------------------------
  for iChild = 1:nChild        % read in each child
    [c cname] = DOMnode2struct(Child.item(iChild-1), Pref);
    if (strcmp(cname,'x0x23text')) % if text node
      if (nChild==1), s=c; end % save only if this is a single child
    else                       % if normal node
      n = f.(cname);           % how many of them in the array so far?        
      if (~isfield(s,cname))   % encountered this name for the first time
        if (n==1)              % if there will be only one of them ...
          s.(cname) = c;       % than save it in format it came in
        else                   % if there will be many of them ...
          s.(cname) = cell(1,n);
          s.(cname){1} = c;    % than save as cell array
        end
        f.(cname) = 1;         % reset the counter
        vec = [vec, n];        % but save array size
      else                     % already have seen this name
        s.(cname){n+1} = c;    % add to the array
        f.(cname) = n+1;       % add to the array counter
      end     
    end % if (strcmp(cname,'TEXT_NODE'))
  end   % for iChild
    
  % --- Post-processing: convert 'struct of arrays' to 'array of struct'
  if (numel(vec)>1 && vec(1)>1 && var(vec)==0)  % convert from struct of
    a = struct2cell(s);                         % arrays to array of struct
    s = cell2struct([a{:}], fieldnames(s), 2);
  end
  % --- Post-processing: remove special 'item' tags ---------------------
  if (isfield(s,Pref.ItemName))
    if (length(fieldnames(s))==1)
      s = s.(Pref.ItemName);         % only child: remove a level
    else
      s.CONTENT = s.(Pref.ItemName); % other children/attributes present use CONTENT
      s = rmfield(s,Pref.ItemName);
    end
  end
end % done dealing with child nodes
  
%% === read in attributes ===============================================
if (node.hasAttributes && Pref.ReadAttr)
  if (~isstruct(s)),               % make into struct if is not already
    ss.CONTENT=s; 
    s=ss; 
  end  
  Attr  = node.getAttributes;     % list of all attributes
  for iAttr = 1:Attr.getLength    % for each attribute
    name  = char(Attr.item(iAttr-1).getName);  % attribute name 
    value = char(Attr.item(iAttr-1).getValue); % attribute value
    if (all(StrIsNum(value))),    % convert to number if possible
      value=str2num(value); 
    end 
    name  = genvarname(name);     % fix name if needed
    s.ATTRIBUTE.(name) = value;   % save again
  end                             % end iAttr loop
end % done with attributes

%% === Post-processing: convert 'cells of structs' to 'arrays of structs' 
if (isstruct(s))  
  fields = fieldnames(s);     % get field names
  for iItem=1:length(s)       % for each struct in the array - usually one
    for iField=1:length(fields)
      field = fields{iField}; % get field name
      x = s(iItem).(field);   
      if (iscell(x) && all(cellfun(@isstruct,x))) % it's cells of structs  
        try                           % this operation fails sometimes 
          s(iItem).(field) = [x{:}];  % converted to arrays of structs
        catch
          if (Pref.NoCells)
            s(iItem).(field) = forceCell2Struct(x);
          end
        end % end catch
      end
    end
  end
end

function s = forceCell2Struct(x) 
% convert cell array of structs, where not all of structs have the same
% fields, to a single array of structs
  AllFields = fieldnames(x{1});     % get field names
  CellMat = cell(length(x), length(AllFields));
  for iItem=1:length(x)      
    fields = fieldnames(x{iItem});  % get field names
    for iField=1:length(fields)
      field = fields{iField};       % get field name
      col = find(strcmp(field,AllFields),1);
      if isempty(col)
        AllFields = [AllFields; field];
        col = length(AllFields);
      end
      CellMat{iItem,col} = x{iItem}.(field);   
    end
  end
  s = cell2struct(CellMat, AllFields, 2);


