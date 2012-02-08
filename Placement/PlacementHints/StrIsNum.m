function out=StrIsNum(str)
% STRISNUM tests if string contains valid number(s). Input can be in form
% of strings or cells of strings. Recognized formats:
% - Numbers: integers, real numbers complex numbers, scientific notation
% - Arrays: single string - space separated, cell arrays of strings
% - Matrices: in same format as output of mat2str
%
% This function is used by xml_read to determine if field should be
% converted to a number or left as a string.
%
% History: Based on Michael Robbins's 'StringIsNumber' function:
% http://www.mathworks.com/matlabcentral/files/6283/StringIsNumber.m
%
% Examples:
% >> StrIsNum(num2str(-1:0.25:1)) % arrays are allowed
%    ans =  1     1     1     1     1     1     1     1    1
% >> StrIsNum(mat2str(rand(5))) % matrices are allowed
%    ans =  1
% >> StrIsNum('123 123. 12.3 .123 +123 -123. +12.3 -.123')
%    ans =     1   1    1    1    1    1     1     1
% >> StrIsNum({'123','.123e4', '-123E+2','+123.e-30','+12.3','-.123'})
%    ans =      1     1         1         1           1       1
% >> StrIsNum({'1.2e++3','123e.4','1+2',' ', '+1.2.3','-+12.3','+.','.'})
%    ans =      0         0        0     0    0        0        0    0
% >> StrIsNum({'1+2i','1.0i +2.0', '1.+ .2i','1e2i +1.2e0'})
%    ans =      1      1           1        1
% >> StrIsNum({'1+2','1.0*i+2.0', '1.i+.2i','1e2+1.2e0'})
%    ans =      0     0            0         0
% >> StrIsNum('-.123')
%    ans =  1
% >> ~isempty(str2num('-.123')) % alternative approach
%    ans =  1
% >> ~isempty(str2num('sphere')) % problem with alternative approach
%    ans =  1
%
% Written by Jarek Tuszynski, SAIC
%

%% simple test first - for NOT a number string
str1 = regexprep(str , '[\d,\+,\-,\.,e,i, ,E,I,\[,\],\;,\,]', '');
if (all(~isempty_(str1))), out=0; return; end

%% clean it up a little
str = lower(strtrim(str)); % Remove leading and trailing white-space from string
str = regexprep(str , '\s+', ' '); % replace multiple spaces with one
str = regexprep(str , ' ?([\+,\-]) ?', '$1', 'once'); %delete spaces around signs
if (all(isempty_(str))), out=0; return; end

%% may be it is a matrix
if (~iscellstr(str) && length(str)>1 && str(1)=='[' && str(end)==']')
  num = str2num(str); % this is something created by mat2str
  out = isnumeric(num);
  return;
end

%% if array of numbers is stored in a space separated string than split it
[tmp, r] = strtok(str);
if (~isempty(r) && ~iscellstr(str))
  str = textscan(str, '%s'); % split into cells
  str = str{1}';
end

%% delete strings that look like numbers
pat = '[\+,\-]?((\d*\.\d+)|(\d+\.?))(e[\+,\-]?\d+)?';
str1=regexprep(str , pat, '', 'once');
str2=regexprep(str1, pat, '', 'once'); % this needed in case of imaginary part of complex number
out = ~isempty_(str) & (isempty_(str1) | strcmp(str2,'i')); % if nothing is left than this was a number


%% ========================================================================
function out = isempty_(str) 
if iscellstr(str)
  out = cellfun('isempty',str);
else
  out = isempty(str); 
end
